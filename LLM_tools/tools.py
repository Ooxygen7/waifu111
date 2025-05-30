import datetime
import logging
from typing import Optional

import ccxt.async_support as ccxt  # 使用异步支持以兼容 Telegram 机器人
import numpy as np  # 用于数值计算
import pandas as pd  # 用于数据处理和技术指标计算
from telegram import Update
from telegram.ext import ContextTypes
from collections import Counter
import bot_core.public_functions.update_parse as public
from bot_core.callback_handlers.inline import Inline
from utils import db_utils as db
from utils.logging_utils import setup_logging

setup_logging()
logger = logging.getLogger(__name__)





class MarketTools:
    """A collection of tools for cryptocurrency market analysis that can be invoked by an LLM."""

    @staticmethod
    async def get_price( symbol: str = "BTC/USDT",
                        exchange: str = "binance") -> str:
        """
        Fetch the current price of a cryptocurrency pair from a specified exchange.
        Description: Retrieves the latest price for a given trading pair (e.g., BTC/USDT) from the specified exchange.
        Type: Query
        Parameters:
            - symbol (string): The trading pair symbol (e.g., BTC/USDT).
            - exchange (string): The exchange to query (default: binance).
        Return Value: A string containing the current price of the specified trading pair.
        Invocation: {"tool_name": "get_price", "parameters": {"symbol": "BTC/USDT", "exchange": "binance"}}
        """
        try:
            exchange_class = getattr(ccxt, exchange.lower(), None)
            if not exchange_class:
                return f"Unsupported exchange: {exchange}. Supported exchanges include 'binance', 'coinbase', etc."
            exchange_instance = exchange_class({'enableRateLimit': True})
            ticker = await exchange_instance.fetch_ticker(symbol)
            price = ticker['last']
            timestamp = ticker['timestamp']
            await exchange_instance.close()
            return f"Current price of {symbol} on {exchange}: {price} USDT (as of {timestamp})."
        except Exception as e:
            logger.error(f"Error fetching price for {symbol} on {exchange}: {str(e)}")
            return f"Failed to fetch price for {symbol} on {exchange}: {str(e)}"

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
    async def get_market_trends(symbol: str = "BTC/USDT",
                                timeframe: str = "1d", limit: int = 30, exchange: str = "binance") -> str:
        """
        Analyze market trends for a cryptocurrency pair based on historical data.
        Description: Analyzes historical data to provide insights on price trends (e.g., bullish, bearish, or neutral).
        Type: Analysis
        Parameters:
            - symbol (string): The trading pair symbol (e.g., BTC/USDT).
            - timeframe (string): The timeframe for analysis (e.g., 1h, 1d).
            - limit (integer): Number of historical data points to analyze (default: 30).
            - exchange (string): The exchange to query (default: binance).
        Return Value: A string summarizing the market trend analysis.
        Invocation: {"tool_name": "get_market_trends", "parameters": {"symbol": "BTC/USDT", "timeframe": "1d", "limit": 30, "exchange": "binance"}}
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
            first_price = closes[0]
            last_price = closes[-1]
            price_change = last_price - first_price
            percentage_change = (price_change / first_price) * 100 if first_price != 0 else 0
            trend = "bullish" if price_change > 0 else "bearish" if price_change < 0 else "neutral"
            trend_desc = (
                f"The price has increased by {price_change:.2f} USDT ({percentage_change:.2f}%) over the last {limit} {timeframe} periods."
                if trend == "bullish" else
                f"The price has decreased by {abs(price_change):.2f} USDT ({percentage_change:.2f}%) over the last {limit} {timeframe} periods."
                if trend == "bearish" else
                f"The price has remained stable over the last {limit} {timeframe} periods."
            )
            await exchange_instance.close()
            return f"Market trend analysis for {symbol} on {exchange}:\n- Trend: {trend.capitalize()}\n- {trend_desc}"
        except Exception as e:
            logger.error(f"Error analyzing market trends for {symbol} on {exchange}: {str(e)}")
            return f"Failed to analyze market trends for {symbol} on {exchange}: {str(e)}"

    @staticmethod
    async def get_volume_analysis( symbol: str = "BTC/USDT",
                                  timeframe: str = "1h", limit: int = 50, exchange: str = "binance") -> str:
        """
        Analyze trading volume for a cryptocurrency pair based on historical data.
        Description: Analyzes historical volume data to identify spikes or trends in trading activity.
        Type: Analysis
        Parameters:
            - symbol (string): The trading pair symbol (e.g., BTC/USDT).
            - timeframe (string): The timeframe for analysis (e.g., 1h, 1d).
            - limit (integer): Number of historical data points to analyze (default: 50).
            - exchange (string): The exchange to query (default: binance).
        Return Value: A string summarizing the volume analysis.
        Invocation: {"tool_name": "get_volume_analysis", "parameters": {"symbol": "BTC/USDT", "timeframe": "1h", "limit": 50, "exchange": "binance"}}
        """
        try:
            exchange_class = getattr(ccxt, exchange.lower(), None)
            if not exchange_class:
                return f"Unsupported exchange: {exchange}. Supported exchanges include 'binance', 'coinbase', etc."
            exchange_instance = exchange_class({'enableRateLimit': True})
            ohlcv = await exchange_instance.fetch_ohlcv(symbol, timeframe, limit=limit)
            if not ohlcv:
                return f"No historical data found for {symbol} on {exchange} with timeframe {timeframe}."
            volumes = [candle[5] for candle in ohlcv]
            avg_volume = sum(volumes) / len(volumes)
            max_volume = max(volumes)
            min_volume = min(volumes)
            recent_volume = volumes[-1]
            volume_trend = "above average" if recent_volume > avg_volume else "below average"
            await exchange_instance.close()
            return (
                f"Volume analysis for {symbol} on {exchange} (timeframe: {timeframe}, last {limit} periods):\n"
                f"- Average Volume: {avg_volume:.2f}\n"
                f"- Highest Volume: {max_volume:.2f}\n"
                f"- Lowest Volume: {min_volume:.2f}\n"
                f"- Recent Volume: {recent_volume:.2f} ({volume_trend})"
            )
        except Exception as e:
            logger.error(f"Error analyzing volume for {symbol} on {exchange}: {str(e)}")
            return f"Failed to analyze volume for {symbol} on {exchange}: {str(e)}"

    @staticmethod
    async def get_rsi( symbol: str = "BTC/USDT",
                      timeframe: str = "1h", limit: int = 50, period: int = 14, exchange: str = "binance") -> str:
        """
        Calculate the Relative Strength Index (RSI) for a cryptocurrency pair.
        Description: Computes the RSI based on historical data to identify overbought or oversold conditions.
        Type: Analysis
        Parameters:
            - symbol (string): The trading pair symbol (e.g., BTC/USDT).
            - timeframe (string): The timeframe for analysis (e.g., 1h, 1d).
            - limit (integer): Number of historical data points to analyze (default: 50).
            - period (integer): Period for RSI calculation (default: 14).
            - exchange (string): The exchange to query (default: binance).
        Return Value: A string summarizing the RSI value and interpretation.
        Invocation: {"tool_name": "get_rsi", "parameters": {"symbol": "BTC/USDT", "timeframe": "1h", "limit": 50, "period": 14, "exchange": "binance"}}
        """
        try:
            exchange_class = getattr(ccxt, exchange.lower(), None)
            if not exchange_class:
                return f"Unsupported exchange: {exchange}. Supported exchanges include 'binance', 'coinbase', etc."
            exchange_instance = exchange_class({'enableRateLimit': True})
            ohlcv = await exchange_instance.fetch_ohlcv(symbol, timeframe, limit=limit)
            if not ohlcv or len(ohlcv) < period:
                return f"Insufficient historical data for {symbol} on {exchange} to calculate RSI."
            closes = np.array([candle[4] for candle in ohlcv])
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
            await exchange_instance.close()
            return f"RSI for {symbol} on {exchange} (timeframe: {timeframe}, period: {period}): {current_rsi:.2f} ({interpretation})"
        except Exception as e:
            logger.error(f"Error calculating RSI for {symbol} on {exchange}: {str(e)}")
            return f"Failed to calculate RSI for {symbol} on {exchange}: {str(e)}"

    @staticmethod
    async def get_moving_average(symbol: str = "BTC/USDT",
                                 timeframe: str = "1h", limit: int = 50, period: int = 20,
                                 exchange: str = "binance") -> str:
        """
        Calculate the Simple Moving Average (SMA) for a cryptocurrency pair.
        Description: Computes the SMA based on historical data to identify price trends.
        Type: Analysis
        Parameters:
            - symbol (string): The trading pair symbol (e.g., BTC/USDT).
            - timeframe (string): The timeframe for analysis (e.g., 1h, 1d).
            - limit (integer): Number of historical data points to analyze (default: 50).
            - period (integer): Period for SMA calculation (default: 20).
            - exchange (string): The exchange to query (default: binance).
        Return Value: A string summarizing the SMA value and trend direction.
        Invocation: {"tool_name": "get_moving_average", "parameters": {"symbol": "BTC/USDT", "timeframe": "1h", "limit": 50, "period": 20, "exchange": "binance"}}
        """
        try:
            exchange_class = getattr(ccxt, exchange.lower(), None)
            if not exchange_class:
                return f"Unsupported exchange: {exchange}. Supported exchanges include 'binance', 'coinbase', etc."
            exchange_instance = exchange_class({'enableRateLimit': True})
            ohlcv = await exchange_instance.fetch_ohlcv(symbol, timeframe, limit=limit)
            if not ohlcv or len(ohlcv) < period:
                return f"Insufficient historical data for {symbol} on {exchange} to calculate SMA."
            closes = [candle[4] for candle in ohlcv]
            sma = sum(closes[-period:]) / period
            current_price = closes[-1]
            trend = "above SMA (bullish signal)" if current_price > sma else "below SMA (bearish signal)"
            await exchange_instance.close()
            return f"SMA ({period}) for {symbol} on {exchange} (timeframe: {timeframe}): {sma:.2f} USDT, current price is {trend}"
        except Exception as e:
            logger.error(f"Error calculating SMA for {symbol} on {exchange}: {str(e)}")
            return f"Failed to calculate SMA for {symbol} on {exchange}: {str(e)}"

    @staticmethod
    async def get_macd( symbol: str = "BTC/USDT",
                       timeframe: str = "1h", limit: int = 50, exchange: str = "binance") -> str:
        """
        Calculate the Moving Average Convergence Divergence (MACD) for a cryptocurrency pair.
        Description: Computes the MACD to identify momentum and potential buy/sell signals.
        Type: Analysis
        Parameters:
            - symbol (string): The trading pair symbol (e.g., BTC/USDT).
            - timeframe (string): The timeframe for analysis (e.g., 1h, 1d).
            - limit (integer): Number of historical data points to analyze (default: 50).
            - exchange (string): The exchange to query (default: binance).
        Return Value: A string summarizing the MACD value and signal interpretation.
        Invocation: {"tool_name": "get_macd", "parameters": {"symbol": "BTC/USDT", "timeframe": "1h", "limit": 50, "exchange": "binance"}}
        """
        try:
            exchange_class = getattr(ccxt, exchange.lower(), None)
            if not exchange_class:
                return f"Unsupported exchange: {exchange}. Supported exchanges include 'binance', 'coinbase', etc."
            exchange_instance = exchange_class({'enableRateLimit': True})
            ohlcv = await exchange_instance.fetch_ohlcv(symbol, timeframe, limit=limit)
            if not ohlcv or len(ohlcv) < 26:
                return f"Insufficient historical data for {symbol} on {exchange} to calculate MACD."
            closes = np.array([candle[4] for candle in ohlcv])
            ema12 = pd.Series(closes).ewm(span=12, adjust=False).mean()
            ema26 = pd.Series(closes).ewm(span=26, adjust=False).mean()
            macd = ema12 - ema26
            signal = macd.ewm(span=9, adjust=False).mean()
            histogram = macd - signal
            current_macd = macd.iloc[-1]
            current_signal = signal.iloc[-1]
            interpretation = (
                "Bullish crossover (buy signal)" if current_macd > current_signal else
                "Bearish crossover (sell signal)"
            )
            await exchange_instance.close()
            return f"MACD for {symbol} on {exchange} (timeframe: {timeframe}): MACD={current_macd:.2f}, Signal={current_signal:.2f} ({interpretation})"
        except Exception as e:
            logger.error(f"Error calculating MACD for {symbol} on {exchange}: {str(e)}")
            return f"Failed to calculate MACD for {symbol} on {exchange}: {str(e)}"

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
    "get_price": MarketTools.get_price,
    "get_historical_data": MarketTools.get_historical_data,
    "get_order_book": MarketTools.get_order_book,
    "get_market_trends": MarketTools.get_market_trends,
    "get_volume_analysis": MarketTools.get_volume_analysis,
    "get_rsi": MarketTools.get_rsi,
    "get_moving_average": MarketTools.get_moving_average,
    "get_macd": MarketTools.get_macd,
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
        Description: Fetches detailed information for a specific user including quotas, balance, and activity.
        Type: Query
        Parameters:
            - user_id (int): The ID of the user to query.
        Return Value: A string with detailed user information.
        Invocation: {"tool_name": "get_user_details", "parameters": {"user_id": 123}}
        """
        query = "SELECT * FROM users WHERE uid = ?"
        result = db.query_db(query, (user_id,))
        if not result:
            return f"No user found with ID {user_id}."
        user = result[0]
        return (f"User Details for ID {user_id}:\n"
                f"Username: {user[1]} {user[2]}\n"
                f"Account Tier: {user[10]}\n"
                f"Remaining Frequency: {user[11]}\n"
                f"Balance: {user[12]}\n"
                f"Conversations: {user[5]}\n"
                f"Dialog Turns: {user[6]}\n"
                f"Input Tokens: {user[8]}\n"
                f"Output Tokens: {user[9]}\n"
                f"Created At: {user[4]}\n"
                f"Updated At: {user[7]}")

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
    async def analyze_user_activity(user_id: int, days: int = 7) -> str:
        """
        Analyze a user's activity over the past specified days.
        Description: Analyzes the user's conversation frequency and token usage over a specified period.
        Type: Analysis
        Parameters:
            - user_id (int): The ID of the user to analyze.
            - days (int, optional): Number of days to look back. Defaults to 7.
        Return Value: A string summarizing the user's activity.
        Invocation: {"tool_name": "analyze_user_activity", "parameters": {"user_id": 123, "days": 7}}
        """
        cutoff_time = (datetime.datetime.now() - datetime.timedelta(days=days)).strftime('%Y-%m-%d %H:%M:%S.%f')
        conv_query = "SELECT COUNT(*) FROM conversations WHERE user_id = ? AND create_at >= ?"
        conv_count = db.query_db(conv_query, (user_id, cutoff_time))[0][0]
        token_query = "SELECT SUM(input_tokens), SUM(output_tokens) FROM users WHERE uid = ?"
        token_data = db.query_db(token_query, (user_id,))[0]
        return (f"Activity Analysis for User ID {user_id} (Last {days} Days):\n"
                f"New Conversations: {conv_count}\n"
                f"Total Input Tokens (All Time): {token_data[0]}\n"
                f"Total Output Tokens (All Time): {token_data[1]}")

    @staticmethod
    async def get_user_sign_history(user_id: int) -> str:
        """
        Retrieve the sign-in history and frequency for a specific user.
        Description: Fetches the user's check-in history and temporary quota information.
        Type: Query
        Parameters:
            - user_id (int): The ID of the user to query.
        Return Value: A string summarizing the user's sign-in history.
        Invocation: {"tool_name": "get_user_sign_history", "parameters": {"user_id": 123}}
        """
        query = "SELECT last_sign, sign_count, frequency FROM user_sign WHERE user_id = ?"
        result = db.query_db(query, (user_id,))
        if not result:
            return f"No sign-in history found for user ID {user_id}."
        sign_data = result[0]
        return (f"Sign-in History for User ID {user_id}:\n"
                f"Last Sign-in: {sign_data[0]}\n"
                f"Total Sign-ins: {sign_data[1]}\n"
                f"Current Temporary Quota: {sign_data[2]}")

    @staticmethod
    async def get_top_active_users(limit: int = 10) -> str:
        """
        Retrieve the most active users based on conversation count or token usage.
        Description: Fetches a list of top users by activity metrics.
        Type: Analysis
        Parameters:
            - limit (int, optional): Number of top users to return. Defaults to 10.
        Return Value: A string summarizing the top active users.
        Invocation: {"tool_name": "get_top_active_users", "parameters": {"limit": 10}}
        """
        query = """
                SELECT uid, user_name, conversations, dialog_turns, input_tokens, output_tokens
                FROM users
                ORDER BY conversations DESC, dialog_turns DESC
                LIMIT ? \
                """
        result = db.query_db(query, (limit,))
        if not result:
            return "No user activity data found."
        summary = "\n".join([f"ID: {row[0]}, Username: {row[1]}, Conversations: {row[2]}, Turns: {row[3]}, "
                             f"Input Tokens: {row[4]}, Output Tokens: {row[5]}" for row in result])
        return f"Top {limit} Active Users:\n{summary}"

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
    async def get_recent_user_conversation_summary(user_id: int) -> str:
        """
        Summarize the most recent conversation of a user for quick insight.
        Description: Fetches and summarizes the latest conversation content for a user.
        Type: Analysis
        Parameters:
            - user_id (int): The ID of the user to analyze.
        Return Value: A string summarizing the latest conversation.
        Invocation: {"tool_name": "get_recent_user_conversation_summary", "parameters": {"user_id": 123}}
        """
        conv_query = "SELECT conv_id FROM conversations WHERE user_id = ? ORDER BY update_at DESC LIMIT 1"
        conv_result = db.query_db(conv_query, (user_id,))
        if not conv_result:
            return f"No conversations found for user ID {user_id}."
        conv_id = conv_result[0][0]
        dialog_query = "SELECT role, raw_content, created_at FROM dialogs WHERE conv_id = ? ORDER BY turn_order LIMIT 5"
        dialogs = db.query_db(dialog_query, (conv_id,))
        summary = "\n".join([f"{row[0]} ({row[2]}): {row[1][:100]}..." for row in dialogs])
        return f"Recent Conversation Summary for User ID {user_id} (Conv ID: {conv_id}):\n{summary}"

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


# Tool mapping for LLM invocation
DATABASE_TOOLS = {
    "get_user_list": DatabaseTools.get_user_list,
    "get_user_details": DatabaseTools.get_user_details,
    "get_user_conversations": DatabaseTools.get_user_conversations,
    "get_conversation_dialog": DatabaseTools.get_conversation_dialog,
    "analyze_user_activity": DatabaseTools.analyze_user_activity,
    "get_user_sign_history": DatabaseTools.get_user_sign_history,
    "get_top_active_users": DatabaseTools.get_top_active_users,
    "get_group_activity": DatabaseTools.get_group_activity,
    "get_system_stats": DatabaseTools.get_system_stats,
    "get_recent_user_conversation_summary": DatabaseTools.get_recent_user_conversation_summary,
    "get_user_config": DatabaseTools.get_user_config,
}
