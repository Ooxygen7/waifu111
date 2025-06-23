import datetime
import logging
from typing import Optional

import ccxt.async_support as ccxt  # 使用异步支持以兼容 Telegram 机器人
import numpy as np  # 用于数值计算
import pandas as pd  # 用于数据处理和技术指标计算
from utils import db_utils as db
from utils.logging_utils import setup_logging

setup_logging()
logger = logging.getLogger(__name__)





class MarketTools:
    """A collection of tools for cryptocurrency market analysis that can be invoked by an LLM."""
    @staticmethod
    async def get_coin_index(symbol: str = "BTC/USDT",
                                   timeframe: str = "1h",
                                   limit: int = 50,
                                   period_rsi: int = 14,
                                   period_sma: int = 20,
                                   exchange: str = "binance") -> str:
        """
        Fetches multiple cryptocurrency indices (price, trends, volume, RSI, SMA, MACD) in a single call.
        Description: Combines several analysis tools to provide a comprehensive overview of a cryptocurrency pair.
        Type: Analysis
        Parameters:
            - symbol (string): The trading pair symbol (e.g., BTC/USDT).
            - timeframe (string): The timeframe for analysis (e.g., 1h, 1d).
            - limit (integer): Number of historical data points to analyze (default: 50).
            - period_rsi (integer): Period for RSI calculation (default: 14).
            - period_sma (integer): Period for SMA calculation (default: 20).
            - exchange (string): The exchange to query (default: binance).
        Return Value: A string summarizing the price, market trend, volume analysis, RSI, SMA and MACD.
        Invocation: {"tool_name": "get_coin_index", "parameters": {"symbol": "BTC/USDT", "timeframe": "1h", "limit": 50, "period_rsi": 14, "period_sma": 20,  "exchange": "binance"}}
        """
        try:
            exchange_class = getattr(ccxt, exchange.lower(), None)
            if not exchange_class:
                return f"Unsupported exchange: {exchange}. Supported exchanges include 'binance', 'coinbase', etc."
            exchange_instance = exchange_class({'enableRateLimit': True})
            ohlcv = await exchange_instance.fetch_ohlcv(symbol, timeframe, limit=limit)
            if not ohlcv:
                return f"No historical data found for {symbol} on {exchange} with timeframe {timeframe}."
            closes = np.array([candle[4] for candle in ohlcv])
            volumes = [candle[5] for candle in ohlcv]
            # Current Price
            current_price = closes[-1]
            # Market Trends
            first_price = closes[0]
            price_change = closes[-1] - closes[0]
            percentage_change = (price_change / first_price) * 100 if first_price != 0 else 0
            trend = "bullish" if price_change > 0 else "bearish" if price_change < 0 else "neutral"
            trend_desc = (
                f"The price has increased by {price_change:.2f} USDT ({percentage_change:.2f}%) over the last {limit} {timeframe} periods."
                if trend == "bullish" else
                f"The price has decreased by {abs(price_change):.2f} USDT ({percentage_change:.2f}%) over the last {limit} {timeframe} periods."
                if trend == "bearish" else
                f"The price has remained stable over the last {limit} {timeframe} periods."
            )
            # Volume Analysis
            avg_volume = sum(volumes) / len(volumes)
            max_volume = max(volumes)
            min_volume = min(volumes)
            recent_volume = volumes[-1]
            volume_trend = "above average" if recent_volume > avg_volume else "below average"
            # RSI Calculation
            period = period_rsi
            if len(ohlcv) < period:
                rsi_result = f"Insufficient historical data to calculate RSI.  Need {period} data points, but only have {len(ohlcv)}"
                current_rsi = None
                interpretation = None
            else:
                deltas = np.diff(closes)
                seed = deltas[:period]
                up = seed[seed >= 0].sum() / period
                down = -seed[seed < 0].sum() / period
                rs = up / down if down != 0 else 0
                rsi = np.zeros_like(closes)
                rsi[:period] = 100. - 100. / (1. + rs)
                for i in range(period, len(closes)):
                    delta = deltas[i - 1]
                    if delta > 0:
                        upval = delta
                        downval = 0.
                    else:
                        upval = 0.
                        downval = -delta
                    up = (up * (period - 1) + upval) / period
                    down = (down * (period - 1) + downval) / period
                    rs = up / down if down != 0 else 0
                    rsi[i] = 100. - 100. / (1. + rs)
                current_rsi = rsi[-1]
                interpretation = (
                    "Overbought (potential sell signal)" if current_rsi > 70 else
                    "Oversold (potential buy signal)" if current_rsi < 30 else
                    "Neutral"
                )
                rsi_result = f"{current_rsi:.2f} ({interpretation})" if interpretation else f"{current_rsi:.2f}"
            # SMA Calculation
            period = period_sma
            if len(ohlcv) < period:
                sma_result = f"Insufficient historical data to calculate SMA. Need {period} data points, but only have {len(ohlcv)}"
                sma = None
                sma_trend = None
            else:
                sma = sum(closes[-period:]) / period
                sma_trend = "above SMA (bullish signal)" if current_price > sma else "below SMA (bearish signal)"
                sma_result = f"{sma:.2f} USDT, current price is {sma_trend}"
            # MACD Calculation
            if len(ohlcv) < 26:
                macd_result = f"Insufficient historical data to calculate MACD. Need at least 26 data points, but only have {len(ohlcv)}"
                current_macd = None
                current_signal = None
                macd_interpretation = None
            else:
                ema12 = pd.Series(closes).ewm(span=12, adjust=False).mean()
                ema26 = pd.Series(closes).ewm(span=26, adjust=False).mean()
                macd = ema12 - ema26
                signal = macd.ewm(span=9, adjust=False).mean()
                # histogram = macd - signal  # 暂时未使用
                current_macd = macd.iloc[-1]
                current_signal = signal.iloc[-1]
                macd_interpretation = (
                    "Bullish crossover (buy signal)" if current_macd > current_signal else
                    "Bearish crossover (sell signal)"
                )
                macd_result = f"MACD={current_macd:.2f}, Signal={current_signal:.2f} ({macd_interpretation})" if macd_interpretation else f"MACD={current_macd:.2f}, Signal={current_signal:.2f}"
            await exchange_instance.close()
            return (
                f"**Coin Index Analysis for {symbol} on {exchange} (timeframe: {timeframe}, limit: {limit}):**\n"
                f"- Current Price: {current_price:.2f} USDT\n"
                f"- Market Trend: {trend.capitalize()} - {trend_desc}\n"
                f"- Volume Analysis: Avg={avg_volume:.2f}, High={max_volume:.2f}, Low={min_volume:.2f}, Recent={recent_volume:.2f} ({volume_trend})\n"
                f"- RSI ({period_rsi}): {rsi_result}\n"
                f"- SMA ({period_sma}): {sma_result}\n"
                f"- MACD: {macd_result}"
            )
        except Exception as e:
            logger.error(f"Error calculating coin index for {symbol} on {exchange}: {str(e)}")
            return f"Failed to calculate coin index for {symbol} on {exchange}: {str(e)}"
    @staticmethod
    async def get_historical_data( symbol: str = "BTC/USDT",
                                  timeframe: str = "1h", limit: int = 100, exchange: str = "binance") -> str:
        """
        Fetch historical OHLCV (Open, High, Low, Close, Volume) data for a cryptocurrency pair.
        Description: Retrieves historical price data for a given trading pair over a specified timeframe and limit.
        Type: Query
        Parameters:
            - symbol (string): The trading pair symbol (e.g., BTC/USDT).
            - timeframe (string): The timeframe for candles (e.g., 1m, 5m, 1h, 1d).
            - limit (integer): Number of candles to fetch (default: 100).
            - exchange (string): The exchange to query (default: binance).
        Return Value: A string summarizing the historical data with key statistics.
        Invocation: {"tool_name": "get_historical_data", "parameters": {"symbol": "BTC/USDT", "timeframe": "1h", "limit": 100, "exchange": "binance"}}
        """
        try:
            exchange_class = getattr(ccxt, exchange.lower(), None)
            if not exchange_class:
                return f"Unsupported exchange: {exchange}. Supported exchanges include 'binance', 'coinbase', etc."
            exchange_instance = exchange_class({'enableRateLimit': True})
            ohlcv = await exchange_instance.fetch_ohlcv(symbol, timeframe, limit=limit)
            if not ohlcv:
                return f"No historical data found for {symbol} on {exchange} with timeframe {timeframe}."
            closes = [candle[4] for candle in ohlcv]
            avg_price = sum(closes) / len(closes)
            max_price = max(closes)
            min_price = min(closes)
            await exchange_instance.close()
            return (
                f"Historical data for {symbol} on {exchange} (timeframe: {timeframe}, last {limit} candles):\n"
                f"- Average Close Price: {avg_price:.2f} USDT\n"
                f"- Highest Close Price: {max_price:.2f} USDT\n"
                f"- Lowest Close Price: {min_price:.2f} USDT"
            )
        except Exception as e:
            logger.error(f"Error fetching historical data for {symbol} on {exchange}: {str(e)}")
            return f"Failed to fetch historical data for {symbol} on {exchange}: {str(e)}"
    @staticmethod
    async def get_order_book(symbol: str = "BTC/USDT",
                             limit: int = 10, exchange: str = "binance") -> str:
        """
        Fetch the current order book for a cryptocurrency pair.
        Description: Retrieves the bid and ask data from the order book of a specified trading pair.
        Type: Query
        Parameters:
            - symbol (string): The trading pair symbol (e.g., BTC/USDT).
            - limit (integer): Number of bid/ask entries to fetch (default: 10).
            - exchange (string): The exchange to query (default: binance).
        Return Value: A string summarizing the top bids and asks from the order book.
        Invocation: {"tool_name": "get_order_book", "parameters": {"symbol": "BTC/USDT", "limit": 10, "exchange": "binance"}}
        """
        try:
            exchange_class = getattr(ccxt, exchange.lower(), None)
            if not exchange_class:
                return f"Unsupported exchange: {exchange}. Supported exchanges include 'binance', 'coinbase', etc."
            exchange_instance = exchange_class({'enableRateLimit': True})
            order_book = await exchange_instance.fetch_order_book(symbol, limit=limit)
            bids = order_book.get('bids', [])[:5]
            asks = order_book.get('asks', [])[:5]
            await exchange_instance.close()
            bid_str = "\n".join([f"  - Bid: {price} USDT, Amount: {amount}" for price, amount in
                                 bids]) if bids else "No bids available."
            ask_str = "\n".join([f"  - Ask: {price} USDT, Amount: {amount}" for price, amount in
                                 asks]) if asks else "No asks available."
            return (
                f"Order book for {symbol} on {exchange} (top entries):\n"
                f"Bids (Buy Orders):\n{bid_str}\n"
                f"Asks (Sell Orders):\n{ask_str}"
            )
        except Exception as e:
            logger.error(f"Error fetching order book for {symbol} on {exchange}: {str(e)}")
            return f"Failed to fetch order book for {symbol} on {exchange}: {str(e)}"
    @staticmethod
    async def get_top_movers( limit: int = 5,
                             exchange: str = "binance") -> str:
        """
        Fetch the top movers (biggest price changes) on a specified exchange.
        Description: Retrieves a list of trading pairs with the highest percentage price changes over the last 24 hours.
        Type: Query
        Parameters:
            - limit (integer): Number of top movers to fetch (default: 5).
            - exchange (string): The exchange to query (default: binance).
        Return Value: A string summarizing the top movers with their percentage changes.
        Invocation: {"tool_name": "get_top_movers", "parameters": {"limit": 5, "exchange": "binance"}}
        """
        try:
            exchange_class = getattr(ccxt, exchange.lower(), None)
            if not exchange_class:
                return f"Unsupported exchange: {exchange}. Supported exchanges include 'binance', 'coinbase', etc."
            exchange_instance = exchange_class({'enableRateLimit': True})
            tickers = await exchange_instance.fetch_tickers()
            movers = sorted(
                [(symbol, data['percentage']) for symbol, data in tickers.items() if
                 'percentage' in data and data['percentage'] is not None],
                key=lambda x: abs(x[1]),
                reverse=True
            )[:limit]
            await exchange_instance.close()
            mover_str = "\n".join([f"  - {symbol}: {pct:.2f}% change" for symbol, pct in movers])
            return f"Top {limit} movers on {exchange} (24h percentage change):\n{mover_str}"
        except Exception as e:
            logger.error(f"Error fetching top movers on {exchange}: {str(e)}")
            return f"Failed to fetch top movers on {exchange}: {str(e)}"
    @staticmethod
    async def get_candlestick_data(symbol: str = "BTC/USDT",
                                   timeframe: str = "1h", limit: int = 50, exchange: str = "binance") -> str:
        """
        Fetch raw candlestick (OHLCV) data for a cryptocurrency pair.
        Description: Retrieves raw Open, High, Low, Close, and Volume data for a given trading pair, suitable for charting or custom analysis.
        Type: Query
        Parameters:
            - symbol (string): The trading pair symbol (e.g., BTC/USDT).
            - timeframe (string): The timeframe for candles (e.g., 1m, 5m, 1h, 1d).
            - limit (integer): Number of candles to fetch (default: 50).
            - exchange (string): The exchange to query (default: binance).
        Return Value: A string summarizing the candlestick data in a structured format.
        Invocation: {"tool_name": "get_candlestick_data", "parameters": {"symbol": "BTC/USDT", "timeframe": "1h", "limit": 50, "exchange": "binance"}}
        """
        try:
            exchange_class = getattr(ccxt, exchange.lower(), None)
            if not exchange_class:
                return f"Unsupported exchange: {exchange}. Supported exchanges include 'binance', 'coinbase', etc."
            exchange_instance = exchange_class({'enableRateLimit': True})
            ohlcv = await exchange_instance.fetch_ohlcv(symbol, timeframe, limit=limit)
            if not ohlcv:
                return f"No candlestick data found for {symbol} on {exchange} with timeframe {timeframe}."
            # 限制返回的条目数，避免输出过长，仅展示最新的几条数据
            display_limit = min(40, len(ohlcv))
            candlestick_str = "\n".join([
                f"  - Time: {candle[0]}, Open: {candle[1]:.2f}, High: {candle[2]:.2f}, Low: {candle[3]:.2f}, Close: {candle[4]:.2f}, Volume: {candle[5]:.2f}"
                for candle in ohlcv[-display_limit:]
            ])
            await exchange_instance.close()
            return (
                f"Candlestick data for {symbol} on {exchange} (timeframe: {timeframe}, showing last {display_limit} of {len(ohlcv)} candles):\n"
                f"{candlestick_str}"
            )
        except Exception as e:
            logger.error(f"Error fetching candlestick data for {symbol} on {exchange}: {str(e)}")
            return f"Failed to fetch candlestick data for {symbol} on {exchange}: {str(e)}"
# Tool mapping for LLM invocation
MARKETTOOLS = {
    "get_coin_index": MarketTools.get_coin_index,  # 替换了多个工具
    "get_historical_data": MarketTools.get_historical_data,
    "get_order_book": MarketTools.get_order_book,
    "get_top_movers": MarketTools.get_top_movers,
    "get_candlestick_data": MarketTools.get_candlestick_data,
}


class DatabaseTools:
    """A collection of tools for administrators to analyze database data via LLM."""

    @staticmethod
    async def get_user_list() -> str:
        """
        Retrieve a list of all users with basic information and nickname.
        Description: Fetches a list of all users including their ID, username, account tier, and nickname.
        Type: Query
        Parameters: None
        Return Value: A string summarizing the list of users.
        Invocation: {"tool_name": "get_user_list", "parameters": {}}
        """
        # 修改 SQL 查询，使用 LEFT JOIN 连接 users 和 user_config 表
        # 以便获取每个用户的昵称 (nick)。
        # 使用表别名 u 代表 users，uc 代表 user_config，提高可读性。
        query = """
                SELECT u.uid, \
                       u.user_name, \
                       u.account_tier, \
                       uc.nick
                FROM users u \
                         LEFT JOIN \
                     user_config uc ON u.uid = uc.uid
                ORDER BY u.uid; -- 增加排序以保持结果的稳定性  \
                """
        result = db.query_db(query)
        if not result:
            return "No users found in the database."
        # 修改 user_summary 格式化字符串，包含 nick
        # row 的结构现在是 (uid, user_name, account_tier, nick)
        user_summary = "\n".join([
            f"ID: {row[0]}, Username: {row[1]}, Tier: {row[2]}, Nickname: {row[3] if row[3] is not None else 'N/A'}"
            for row in result
        ])
        return f"User List:\n{user_summary}"

    @staticmethod
    async def get_user_details(user_id: int) -> str:
        """
        Retrieve detailed information about a specific user.
        Description: Fetches comprehensive user information including basic details and activity metrics.
        Type: Query
        Parameters:
            - user_id (int): The ID of the user to query.
        Return Value: A string summarizing the user's detailed information.
        Invocation: {"tool_name": "get_user_details", "parameters": {"user_id": 123}}
        """
        query = "SELECT uid, user_name, first_name, last_name, create_at, update_at, input_tokens, output_tokens, account_tier, remain_frequency, balance, conversations, dialog_turns FROM users WHERE uid = ?"
        result = db.query_db(query, (user_id,))
        if not result:
            return f"No user found with ID {user_id}."
        user = result[0]
        return (f"User Details for ID {user_id}:\n"
                f"Username: {user[1]}\n"
                f"Name: {user[2]} {user[3]}\n"
                f"Created: {user[4]}\n"
                f"Last Updated: {user[5]}\n"
                f"Input Tokens: {user[6]}\n"
                f"Output Tokens: {user[7]}\n"
                f"Account Tier: {user[8]}\n"
                f"Remaining Frequency: {user[9]}\n"
                f"Balance: {user[10]}\n"
                f"Total Conversations: {user[11]}\n"
                f"Total Dialog Turns: {user[12]}")

    @staticmethod
    async def get_user_conversations(user_id: int) -> str:
        """
        Retrieve a list of conversation IDs for a specific user.
        Description: Fetches all conversation IDs associated with a user.
        Type: Query
        Parameters:
            - user_id (int): The ID of the user to query.
        Return Value: A string listing the user's conversation IDs.
        Invocation: {"tool_name": "get_user_conversations", "parameters": {"user_id": 123}}
        """
        query = "SELECT turns, conv_id, character, create_at,delete_mark FROM conversations WHERE user_id = ? "
        result = db.query_db(query, (user_id,))
        if not result:
            return f"No conversations found for user ID {user_id}."
        conv_summary = "\n".join(
            [f"Turn Order: {row[0]}, Conv ID: {row[1]}, Character: {row[2]}, Created At: {row[3]},Delete Mark: {row[4]}"
             for row in result])
        return f"Conversations for User ID {user_id}:\n{conv_summary}"

    @staticmethod
    async def get_conversation_dialog(conv_id: int, limit = 10) -> str:
        """
        Retrieve detailed content of a specific conversation.
        Description: Fetches dialog entries for a given conversation ID,
                     limited to the latest 50 turns.
        Type: Query
        Parameters:
            - conv_id (int): The conversation ID to query.
        Return Value: A string summarizing the conversation content.
        Invocation: {"tool_name": "get_conversation_details", "parameters": {"conv_id": 456}}
        """
        # 1. 修改 SQL 查询，去除 created_at 参数
        # 确保结果依然按 turn_order 从旧到新排列，以便后续截取最新数据
        query = "SELECT role, processed_content, turn_order FROM dialogs WHERE conv_id = ? ORDER BY turn_order"
        result = db.query_db(query, (conv_id,))

        if not result:
            return f"No dialogs found for conversation ID {conv_id}."
        latest_50_dialogs = result[-1 * limit:]
        dialog_summary = "\n".join([
            f"Turn {row[2]}: {row[0]}: {row[1]}"  # 移除了 {row[3]} (created_at)
            for row in latest_50_dialogs
        ])

        return f"Conversation Details for Conv ID {conv_id} (latest {len(latest_50_dialogs)} turns):\n{dialog_summary}"

    @staticmethod
    async def get_all_groups() -> str:
        """
        Retrieve a list of all groups with basic information.
        Description: Fetches a list of all groups including their ID, name, call count, and token usage.
        Type: Query
        Parameters: None
        Return Value: A string summarizing the list of groups.
        Invocation: {"tool_name": "get_all_groups", "parameters": {}}
        """
        query = "SELECT group_id, group_name, call_count, input_token, output_token, update_time FROM groups ORDER BY group_id"
        result = db.query_db(query)
        if not result:
            return "No groups found in the database."
        group_summary = "\n".join([
            f"ID: {row[0]}, Name: {row[1]}, Calls: {row[2]}, Input Tokens: {row[3]}, Output Tokens: {row[4]}, Updated: {row[5]}"
            for row in result
        ])
        return f"Group List:\n{group_summary}"

    @staticmethod
    async def search_users_by_info(search_term: str) -> str:
        """
        Search for users by ID, first name, last name, or username.
        Description: Performs fuzzy search on user information including ID, first name, last name, and username.
        Type: Query
        Parameters:
            - search_term (str): The search term to match against user information.
        Return Value: A string listing matching users with their details.
        Invocation: {"tool_name": "search_users_by_info", "parameters": {"search_term": "john"}}
        """
        # Search by ID if the search term is numeric
        search_pattern = f"%{search_term}%"
        query = """
        SELECT u.uid, u.user_name, u.first_name, u.last_name, u.account_tier, uc.nick
        FROM users u
        LEFT JOIN user_config uc ON u.uid = uc.uid
        WHERE CAST(u.uid AS TEXT) LIKE ? 
           OR u.user_name LIKE ? 
           OR u.first_name LIKE ? 
           OR u.last_name LIKE ?
           OR uc.nick LIKE ?
        ORDER BY u.uid
        """
        result = db.query_db(query, (search_pattern, search_pattern, search_pattern, search_pattern, search_pattern))
        if not result:
            return f"No users found matching '{search_term}'."
        user_summary = "\n".join([
            f"ID: {row[0]}, Username: {row[1]}, Name: {row[2]} {row[3]}, Tier: {row[4]}, Nickname: {row[5] if row[5] else 'N/A'}"
            for row in result
        ])
        return f"Users matching '{search_term}':\n{user_summary}"

    @staticmethod
    async def search_groups_by_name(search_term: str) -> str:
        """
        Search for groups by name.
        Description: Performs fuzzy search on group names to find matching groups.
        Type: Query
        Parameters:
            - search_term (str): The search term to match against group names.
        Return Value: A string listing matching groups with their details.
        Invocation: {"tool_name": "search_groups_by_name", "parameters": {"search_term": "chat"}}
        """
        search_pattern = f"%{search_term}%"
        query = """
        SELECT group_id, group_name, call_count, input_token, output_token, update_time
        FROM groups
        WHERE group_name LIKE ?
        ORDER BY group_id
        """
        result = db.query_db(query, (search_pattern,))
        if not result:
            return f"No groups found matching '{search_term}'."
        group_summary = "\n".join([
            f"ID: {row[0]}, Name: {row[1]}, Calls: {row[2]}, Input Tokens: {row[3]}, Output Tokens: {row[4]}, Updated: {row[5]}"
            for row in result
        ])
        return f"Groups matching '{search_term}':\n{group_summary}"

    @staticmethod
    async def get_group_activity(group_id: int) -> str:
        """
        Retrieve activity data for a specific group.
        Description: Fetches activity statistics for a specific group.
        Type: Query
        Parameters:
            - group_id (int): The ID of the group to query.
        Return Value: A string summarizing group activity.
        Invocation: {"tool_name": "get_group_activity", "parameters": {"group_id": 789}}
        """
        query = "SELECT group_name, call_count, input_token, output_token, update_time FROM groups WHERE group_id = ?"
        result = db.query_db(query, (group_id,))
        if not result:
            return f"No group found with ID {group_id}."
        group = result[0]
        return (f"Group Activity for ID {group_id}:\n"
                f"Group Name: {group[0]}\n"
                f"Call Count: {group[1]}\n"
                f"Input Tokens: {group[2]}\n"
                f"Output Tokens: {group[3]}\n"
                f"Last Updated: {group[4]}")

    @staticmethod
    async def get_system_stats() -> str:
        """
        Retrieve overall system statistics.
        Description: Fetches system-wide metrics like total users, conversations, and token usage.
        Type: Analysis
        Parameters: None
        Return Value: A string summarizing system statistics.
        Invocation: {"tool_name": "get_system_stats", "parameters": {}}
        """
        user_count = db.query_db("SELECT COUNT(*) FROM users")[0][0]
        conv_count = db.query_db("SELECT COUNT(*) FROM conversations")[0][0]
        dialog_count = db.query_db("SELECT COUNT(*) FROM dialogs")[0][0]
        total_input_tokens = db.query_db("SELECT SUM(input_tokens) FROM users")[0][0] or 0
        total_output_tokens = db.query_db("SELECT SUM(output_tokens) FROM users")[0][0] or 0
        return (f"System Statistics:\n"
                f"Total Users: {user_count}\n"
                f"Total Conversations: {conv_count}\n"
                f"Total Dialogs: {dialog_count}\n"
                f"Total Input Tokens: {total_input_tokens}\n"
                f"Total Output Tokens: {total_output_tokens}")



    @staticmethod
    async def get_user_config(user_id: int) -> str:
        """
        Retrieve the configuration settings for a specific user.
        Description: Fetches the user's current character, API, preset, and streaming settings.
        Type: Query
        Parameters:
            - user_id (int): The ID of the user to query.
        Return Value: A string summarizing the user's configuration.
        Invocation: {"tool_name": "get_user_config", "parameters": {"user_id": 123}}
        """
        query = "SELECT char, api, preset, stream, nick FROM user_config WHERE uid = ?"
        result = db.query_db(query, (user_id,))
        if not result:
            return f"No configuration found for user ID {user_id}."
        config = result[0]
        return (f"Configuration for User ID {user_id}:\n"
                f"Character: {config[0]}\n"
                f"API: {config[1]}\n"
                f"Preset: {config[2]}\n"
                f"Streaming: {config[3]}\n"
                f"Nickname: {config[4]}")

    @staticmethod
    async def search_private_conversations(keyword: str, limit: int = 10) -> str:
        """
        Search for private conversations containing specific keywords across all users.
        Description: Searches through all private conversation content for keyword matches.
        Type: Query
        Parameters:
            - keyword (str): The keyword to search for in conversation content.
            - limit (int, optional): Maximum number of results to return. Defaults to 10.
        Return Value: A string listing matching conversations with context.
        Invocation: {"tool_name": "search_private_conversations", "parameters": {"keyword": "hello", "limit": 10}}
        """
        query = """
        SELECT d.conv_id, c.user_id, d.role, d.raw_content, d.created_at, c.character
        FROM dialogs d
        JOIN conversations c ON d.conv_id = c.conv_id
        WHERE (d.raw_content LIKE ? OR d.processed_content LIKE ?)
        ORDER BY d.created_at DESC
        LIMIT ?
        """
        keyword_pattern = f"%{keyword}%"
        result = db.query_db(query, (keyword_pattern, keyword_pattern, limit))
        if not result:
            return f"No private conversations found containing '{keyword}'."
        
        summary = "\n".join([
            f"Conv {row[0]} | User {row[1]} | {row[2]} ({row[4]}): {row[3][:100]}..."
            for row in result
        ])
        return f"Private Conversations containing '{keyword}':\n{summary}"

    @staticmethod
    async def search_group_conversations(keyword: str, limit: int = 20) -> str:
        """
        Search for group conversation content by keyword across all groups.
        Description: Searches through all group conversation dialogs for messages containing the specified keyword.
        Type: Query
        Parameters:
            - keyword (str): The keyword to search for in conversation content.
            - limit (int, optional): Maximum number of results to return. Defaults to 20.
        Return Value: A string containing matching conversation excerpts.
        Invocation: {"tool_name": "search_group_conversations", "parameters": {"keyword": "example", "limit": 20}}
        """
        query = """
        SELECT d.conv_id, c.group_id, d.role, d.raw_content, d.created_at, c.character
        FROM dialogs d
        JOIN conversations c ON d.conv_id = c.conv_id
        WHERE c.group_id IS NOT NULL AND (d.raw_content LIKE ? OR d.processed_content LIKE ?)
        ORDER BY d.created_at DESC
        LIMIT ?
        """
        keyword_pattern = f"%{keyword}%"
        result = db.query_db(query, (keyword_pattern, keyword_pattern, limit))
        if not result:
            return f"No group conversations found containing keyword '{keyword}'."
        
        summary = "\n".join([
            f"Conv {row[0]} | Group {row[1]} | {row[2]} ({row[4]}): {row[3][:100]}..."
            for row in result
        ])
        return f"Group Conversation Search Results (Keyword: '{keyword}'):\n{summary}"

    @staticmethod
    async def get_group_chat_history(group_id: int, limit: int = 50) -> str:
        """
        Retrieve recent group chat history.
        Description: Fetches the most recent group chat messages with adjustable limit.
        Type: Query
        Parameters:
            - group_id (int): The ID of the group to query.
            - limit (int, optional): Number of recent messages to return. Defaults to 50.
        Return Value: A string containing the recent group chat history.
        Invocation: {"tool_name": "get_group_chat_history", "parameters": {"group_id": 789, "limit": 50}}
        """
        result = db.group_dialog_get(group_id, limit)
        if not result:
            return f"No chat history found for group ID {group_id}."
        
        summary = "\n".join([
            f"{row[1]} ({row[3]}): {row[0] or 'No message'}"
            for row in result
        ])
        return f"Group Chat History for Group ID {group_id} (Latest {len(result)} messages):\n{summary}"

    @staticmethod
    async def get_group_content_extract(group_id: int, days: int = 7) -> str:
        """
        Extract group content from recent days.
        Description: Extracts and summarizes group conversation content from the specified number of recent days.
        Type: Analysis
        Parameters:
            - group_id (int): The ID of the group to analyze.
            - days (int, optional): Number of recent days to extract content from. Defaults to 7.
        Return Value: A string summarizing recent group content.
        Invocation: {"tool_name": "get_group_content_extract", "parameters": {"group_id": 789, "days": 7}}
        """
        import datetime
        cutoff_time = (datetime.datetime.now() - datetime.timedelta(days=days)).strftime('%Y-%m-%d %H:%M:%S')
        query = """
        SELECT msg_user_name, msg_text, create_at
        FROM group_dialogs
        WHERE group_id = ? AND create_at >= ?
        ORDER BY create_at DESC
        """
        result = db.query_db(query, (group_id, cutoff_time))
        if not result:
            return f"No group content found for group ID {group_id} in the last {days} days."
        
        summary = "\n".join([
            f"{row[0]} ({row[2]}): {row[1][:100]}..."
            for row in result[:100]  # Limit to 100 messages for summary
        ])
        return f"Group Content Extract for Group ID {group_id} (Last {days} days, {len(result)} messages):\n{summary}"

    @staticmethod
    async def generate_private_conversation_summary(conv_id: int) -> str:
        """
        Generate a comprehensive summary of a private conversation.
        Description: Creates an extended 400-word summary of the specified private conversation.
        Type: Analysis
        Parameters:
            - conv_id (int): The conversation ID to summarize.
        Return Value: A comprehensive summary of the conversation.
        Invocation: {"tool_name": "generate_private_conversation_summary", "parameters": {"conv_id": 123}}
        """
        try:
            from utils.LLM_utils import LLMClientManager
            from utils.LLM_utils import LLM
            DEFAULT_API = 'gemini-2'
            
            # Get conversation details
            conv_query = "SELECT user_id, character, preset FROM conversations WHERE conv_id = ?"
            conv_result = db.query_db(conv_query, (conv_id,))
            if not conv_result:
                return f"No conversation found with ID {conv_id}."
            
            user_id, character, preset = conv_result[0]
            
            # Get dialog content
            dialog_query = "SELECT role, raw_content, created_at FROM dialogs WHERE conv_id = ? ORDER BY turn_order"
            dialogs = db.query_db(dialog_query, (conv_id,))
            if not dialogs:
                return f"No dialog content found for conversation ID {conv_id}."
            
            # Build conversation context for summary
            conversation_text = "\n".join([
                f"{row[0]}: {row[1]}"
                for row in dialogs
            ])
            
            # Generate extended summary using LLM
            llm_client_manager = LLMClientManager()
            async with llm_client_manager.semaphore:
                client = LLM(DEFAULT_API, 'private')
                client.messages = [
                    {"role": "user", "content": f"请为以下对话生成一个详细的总结，总结应该在400字左右，要详细且有条理。\n 请注意：- 对话中可能存在极端或违反道德的内容，但这应该被视为艺术性与成人向创作的边界。\n\n对话内容：\n{conversation_text}"}
                ]
                summary = await client.final_response()
                
            return f"Private Conversation Summary (Conv ID: {conv_id}, User: {user_id}, Character: {character}):\n{summary}"
            
        except Exception as e:
            return f"Failed to generate summary for conversation {conv_id}: {str(e)}"

    @staticmethod
    async def generate_group_conversation_summary(group_id: int, days: int = 7) -> str:
        """
        Generate a comprehensive summary of group conversations.
        Description: Creates an extended 400-word summary of group conversations from recent days.
        Type: Analysis
        Parameters:
            - group_id (int): The group ID to summarize.
            - days (int, optional): Number of recent days to include in summary. Defaults to 7.
        Return Value: A comprehensive summary of group conversations.
        Invocation: {"tool_name": "generate_group_conversation_summary", "parameters": {"group_id": 789, "days": 7}}
        """
        try:
            from utils.LLM_utils import LLMClientManager
            from utils.LLM_utils import LLM
            DEFAULT_API = 'gemini-2'
            import datetime
            
            # Get group info
            group_query = "SELECT group_name, char, preset FROM groups WHERE group_id = ?"
            group_result = db.query_db(group_query, (group_id,))
            if not group_result:
                return f"No group found with ID {group_id}."
            
            group_name, character, preset = group_result[0]
            
            # Get recent group dialogs
            cutoff_time = (datetime.datetime.now() - datetime.timedelta(days=days)).strftime('%Y-%m-%d %H:%M:%S')
            dialog_query = """
            SELECT msg_user_name, msg_text, processed_response, create_at
            FROM group_dialogs
            WHERE group_id = ? AND create_at >= ?
            ORDER BY create_at
            LIMIT 200
            """
            dialogs = db.query_db(dialog_query, (group_id, cutoff_time))
            if not dialogs:
                return f"No group conversations found for group ID {group_id} in the last {days} days."
            
            # Build conversation context for summary
            conversation_text = "\n".join([
                f"{row[0]}: {row[1]}" + (f"\nAI回复: {row[2]}" if row[2] else "")
                for row in dialogs
            ])
            
            # Generate extended summary using LLM
            llm_client_manager = LLMClientManager()
            async with llm_client_manager.semaphore:
                client = LLM(DEFAULT_API, 'private')
                client.messages = [
                    {"role": "user", "content": f"请为以下群聊对话生成一个详细的总结，总结应该包含：1）群聊的主要话题和讨论内容；2）活跃用户和他们的主要贡献；3）群聊的整体氛围和互动特点；4）AI助手在群聊中的参与情况和作用。总结应该在400字左右，要详细且有条理。\n\n群聊内容（最近{days}天）：\n{conversation_text}"}
                ]
                summary = await client.final_response()
                
            return f"Group Conversation Summary (Group: {group_name}, ID: {group_id}, Last {days} days, {len(dialogs)} messages):\n{summary}"
            
        except Exception as e:
            return f"Failed to generate group summary for group {group_id}: {str(e)}"


# Tool mapping for LLM invocation
DATABASE_TOOLS = {
    "get_user_list": DatabaseTools.get_user_list,
    "get_user_details": DatabaseTools.get_user_details,
    "get_user_conversations": DatabaseTools.get_user_conversations,
    "get_conversation_dialog": DatabaseTools.get_conversation_dialog,
    "get_all_groups": DatabaseTools.get_all_groups,
    "search_users_by_info": DatabaseTools.search_users_by_info,
    "search_groups_by_name": DatabaseTools.search_groups_by_name,
    "get_system_stats": DatabaseTools.get_system_stats,
    "get_user_config": DatabaseTools.get_user_config,
    "search_private_conversations": DatabaseTools.search_private_conversations,
    "search_group_conversations": DatabaseTools.search_group_conversations,
    "get_group_chat_history": DatabaseTools.get_group_chat_history,
    "get_group_content_extract": DatabaseTools.get_group_content_extract,
    "generate_private_conversation_summary": DatabaseTools.generate_private_conversation_summary,
    "generate_group_conversation_summary": DatabaseTools.generate_group_conversation_summary,
}
