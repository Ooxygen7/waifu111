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

"""
用于构建交由LLM调用的工具
"""



class MarketTools:
    """A collection of tools for cryptocurrency market analysis that can be invoked by an LLM."""
    @staticmethod
    async def get_coin_index(symbol: str = "BTC/USDT",
                                   timeframe: str = "1h",
                                   limit: int = 50,
                                   period_rsi: int = 14,
                                   period_sma: int = 20,
                                   exchange: str = "binance") -> dict:
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
        Return Value: A dictionary with 'display' for user and 'llm_feedback' for AI.
        Invocation: {"tool_name": "get_coin_index", "parameters": {"symbol": "BTC/USDT", "timeframe": "1h", "limit": 50, "period_rsi": 14, "period_sma": 20,  "exchange": "binance"}}
        """
        try:
            exchange_class = getattr(ccxt, exchange.lower(), None)
            if not exchange_class:
                error_msg = f"Unsupported exchange: {exchange}. Supported exchanges include 'binance', 'bybit', 'okx', 'gateio', etc."
                return {"display": error_msg, "llm_feedback": error_msg}

            exchange_instance = exchange_class({'enableRateLimit': True})
            
            try_symbol = symbol
            if '/USDT' in symbol and not symbol.endswith(':USDT'):
                base_symbol = symbol.split('/')[0]
                try_symbol = f"{base_symbol}/USDT:USDT"
            
            try:
                ohlcv = await exchange_instance.fetch_ohlcv(try_symbol, timeframe, limit=limit)
                symbol = try_symbol
            except Exception:
                ohlcv = await exchange_instance.fetch_ohlcv(symbol, timeframe, limit=limit)
                
            if not ohlcv:
                error_msg = f"No historical data found for {symbol} on {exchange} with timeframe {timeframe}."
                return {"display": error_msg, "llm_feedback": error_msg}
                
            closes = np.array([candle[4] for candle in ohlcv])
            volumes = [candle[5] for candle in ohlcv]
            
            price_decimal_places = 0
            volume_decimal_places = 0
            if len(closes) > 0:
                price_str = str(closes[0])
                if '.' in price_str:
                    price_decimal_places = len(price_str.split('.')[1])
            if len(volumes) > 0:
                volume_str = str(volumes[0])
                if '.' in volume_str:
                    volume_decimal_places = len(volume_str.split('.')[1])
            
            price_format = f"{{:.{price_decimal_places}f}}"
            volume_format = f"{{:.{volume_decimal_places}f}}"
            
            current_price = closes[-1]
            
            first_price = closes[0]
            price_change = closes[-1] - closes[0]
            percentage_change = (price_change / first_price) * 100 if first_price != 0 else 0
            trend = "bullish" if price_change > 0 else "bearish" if price_change < 0 else "neutral"
            trend_desc = (
                f"The price has increased by {price_format.format(price_change)} USDT ({percentage_change:.2f}%) over the last {limit} {timeframe} periods."
                if trend == "bullish" else
                f"The price has decreased by {price_format.format(abs(price_change))} USDT ({percentage_change:.2f}%) over the last {limit} {timeframe} periods."
                if trend == "bearish" else
                f"The price has remained stable over the last {limit} {timeframe} periods."
            )
            
            avg_volume = sum(volumes) / len(volumes)
            max_volume = max(volumes)
            min_volume = min(volumes)
            recent_volume = volumes[-1]
            volume_trend = "above average" if recent_volume > avg_volume else "below average"
            
            period = period_rsi
            if len(ohlcv) < period:
                rsi_result = f"Insufficient data for RSI ({len(ohlcv)}/{period})"
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
                    upval = delta if delta > 0 else 0.
                    downval = -delta if delta < 0 else 0.
                    up = (up * (period - 1) + upval) / period
                    down = (down * (period - 1) + downval) / period
                    rs = up / down if down != 0 else 0
                    rsi[i] = 100. - 100. / (1. + rs)
                current_rsi = rsi[-1]
                interpretation = "Overbought" if current_rsi > 70 else "Oversold" if current_rsi < 30 else "Neutral"
                rsi_result = f"{current_rsi:.2f} ({interpretation})"
            
            period = period_sma
            if len(ohlcv) < period:
                sma_result = f"Insufficient data for SMA ({len(ohlcv)}/{period})"
            else:
                sma = sum(closes[-period:]) / period
                sma_trend = "above SMA (bullish)" if current_price > sma else "below SMA (bearish)"
                sma_result = f"{price_format.format(sma)} USDT, price is {sma_trend}"
            
            if len(ohlcv) < 26:
                macd_result = f"Insufficient data for MACD ({len(ohlcv)}/26)"
            else:
                ema12 = pd.Series(closes).ewm(span=12, adjust=False).mean()
                ema26 = pd.Series(closes).ewm(span=26, adjust=False).mean()
                macd = ema12 - ema26
                signal = macd.ewm(span=9, adjust=False).mean()
                current_macd = macd.iloc[-1]
                current_signal = signal.iloc[-1]
                macd_interpretation = "Bullish crossover" if current_macd > current_signal else "Bearish crossover"
                macd_result = f"MACD={price_format.format(current_macd)}, Signal={price_format.format(current_signal)} ({macd_interpretation})"
            
            await exchange_instance.close()

            display_output = (
                f"**Coin Index Analysis for {symbol} on {exchange} (timeframe: {timeframe}, limit: {limit}):**\n"
                f"- Current Price: {price_format.format(current_price)} USDT\n"
                f"- Market Trend: {trend.capitalize()} - {trend_desc}\n"
                f"- Volume Analysis: Avg={volume_format.format(avg_volume)}, High={volume_format.format(max_volume)}, Low={volume_format.format(min_volume)}, Recent={volume_format.format(recent_volume)} ({volume_trend})\n"
                f"- RSI ({period_rsi}): {rsi_result}\n"
                f"- SMA ({period_sma}): {sma_result}\n"
                f"- MACD: {macd_result}"
            )
            
            llm_feedback = (
                f"Analysis for {symbol}:\n"
                f"- Price: {price_format.format(current_price)} USDT\n"
                f"- Trend: {trend.capitalize()}\n"
                f"- RSI: {rsi_result}\n"
                f"- SMA: {sma_result}\n"
                f"- MACD: {macd_result}"
            )

            return {"display": display_output, "llm_feedback": llm_feedback}

        except Exception as e:
            logger.error(f"Error calculating coin index for {symbol} on {exchange}: {str(e)}")
            error_msg = f"Failed to calculate coin index for {symbol} on {exchange}: {str(e)}"
            return {"display": error_msg, "llm_feedback": error_msg}
    @staticmethod
    async def get_historical_data( symbol: str = "BTC/USDT",
                                  timeframe: str = "1h", limit: int = 100, exchange: str = "binance") -> dict:
        """
        Fetch historical OHLCV (Open, High, Low, Close, Volume) data for a cryptocurrency pair.
        Description: Retrieves historical price data for a given trading pair over a specified timeframe and limit.
        Type: Query
        Parameters:
            - symbol (string): The trading pair symbol (e.g., BTC/USDT).
            - timeframe (string): The timeframe for candles (e.g., 1m, 5m, 1h, 1d).
            - limit (integer): Number of candles to fetch (default: 100).
            - exchange (string): The exchange to query (default: binance).
        Return Value: A dictionary with 'display' for user and 'llm_feedback' for AI.
        Invocation: {"tool_name": "get_historical_data", "parameters": {"symbol": "BTC/USDT", "timeframe": "1h", "limit": 100, "exchange": "binance"}}
        """
        try:
            exchange_class = getattr(ccxt, exchange.lower(), None)
            if not exchange_class:
                error_msg = f"Unsupported exchange: {exchange}. Supported exchanges include 'binance', 'bybit', 'okx', 'gateio', etc."
                return {"display": error_msg, "llm_feedback": error_msg}

            exchange_instance = exchange_class({'enableRateLimit': True})
            
            try_symbol = symbol
            if '/USDT' in symbol and not symbol.endswith(':USDT'):
                base_symbol = symbol.split('/')[0]
                try_symbol = f"{base_symbol}/USDT:USDT"
            
            try:
                ohlcv = await exchange_instance.fetch_ohlcv(try_symbol, timeframe, limit=limit)
                symbol = try_symbol
            except Exception:
                ohlcv = await exchange_instance.fetch_ohlcv(symbol, timeframe, limit=limit)
                
            if not ohlcv:
                error_msg = f"No historical data found for {symbol} on {exchange} with timeframe {timeframe}."
                return {"display": error_msg, "llm_feedback": error_msg}
                
            closes = [candle[4] for candle in ohlcv]
            avg_price = sum(closes) / len(closes)
            max_price = max(closes)
            min_price = min(closes)
            
            decimal_places = 0
            if closes:
                price_str = str(closes[0])
                if '.' in price_str:
                    decimal_places = len(price_str.split('.')[1])
            
            format_str = f"{{:.{decimal_places}f}}"
            
            await exchange_instance.close()
            
            result_str = (
                f"Historical data for {symbol} on {exchange} (timeframe: {timeframe}, last {limit} candles):\n"
                f"- Average Close Price: {format_str.format(avg_price)} USDT\n"
                f"- Highest Close Price: {format_str.format(max_price)} USDT\n"
                f"- Lowest Close Price: {format_str.format(min_price)} USDT"
            )
            return {"display": result_str, "llm_feedback": result_str}

        except Exception as e:
            logger.error(f"Error fetching historical data for {symbol} on {exchange}: {str(e)}")
            error_msg = f"Failed to fetch historical data for {symbol} on {exchange}: {str(e)}"
            return {"display": error_msg, "llm_feedback": error_msg}
    @staticmethod
    async def get_market_depth(symbol: str = "BTC/USDT",
                             depth: int = 10, exchange: str = "binance") -> dict:
        """
        Fetch the market depth data for a cryptocurrency pair.
        Description: Retrieves detailed order book depth data showing buy/sell pressure at different price levels.
        Type: Query
        Parameters:
            - symbol (string): The trading pair symbol (e.g., BTC/USDT).
            - depth (integer): Depth of order book to analyze (default: 10).
            - exchange (string): The exchange to query (default: binance).
        Return Value: A dictionary with 'display' for user and 'llm_feedback' for AI.
        Invocation: {"tool_name": "get_market_depth", "parameters": {"symbol": "BTC/USDT", "depth": 10, "exchange": "binance"}}
        """
        try:
            exchange_class = getattr(ccxt, exchange.lower(), None)
            if not exchange_class:
                error_msg = f"Unsupported exchange: {exchange}. Supported exchanges include 'binance', 'bybit', 'okx', 'gateio', etc."
                return {"display": error_msg, "llm_feedback": error_msg}

            exchange_instance = exchange_class({'enableRateLimit': True})
            
            try_symbol = symbol
            if '/USDT' in symbol and not symbol.endswith(':USDT'):
                base_symbol = symbol.split('/')[0]
                try_symbol = f"{base_symbol}/USDT:USDT"
            
            try:
                order_book = await exchange_instance.fetch_order_book(try_symbol, limit=depth*5)
                symbol = try_symbol
            except Exception:
                order_book = await exchange_instance.fetch_order_book(symbol, limit=depth*5)
            
            bids = order_book.get('bids', [])
            asks = order_book.get('asks', [])

            if not bids and not asks:
                error_msg = f"No order book data found for {symbol} on {exchange}."
                return {"display": error_msg, "llm_feedback": error_msg}

            current_price = (bids[0][0] + asks[0][0]) / 2 if bids and asks else (bids[0][0] if bids else asks[0][0])
            
            total_bid_volume = sum(amount for price, amount in bids[:depth])
            total_ask_volume = sum(amount for price, amount in asks[:depth])
            
            buy_sell_ratio = total_bid_volume / total_ask_volume if total_ask_volume > 0 else float('inf')
            
            if buy_sell_ratio > 1.5:
                pressure_analysis = f"强烈买入压力 (买/卖比率: {buy_sell_ratio:.2f})"
            elif buy_sell_ratio < 0.67:
                pressure_analysis = f"强烈卖出压力 (买/卖比率: {buy_sell_ratio:.2f})"
            else:
                pressure_analysis = f"买卖压力平衡 (买/卖比率: {buy_sell_ratio:.2f})"
            
            decimal_places = 0
            if bids:
                price_str = str(bids[0][0])
                if '.' in price_str:
                    decimal_places = len(price_str.split('.')[1])
            price_format = f"{{:.{decimal_places}f}}"

            support_levels = [bids[i][0] for i in range(1, len(bids)-1) if bids[i][1] > bids[i-1][1] and bids[i][1] > bids[i+1][1]][:3]
            resistance_levels = [asks[i][0] for i in range(1, len(asks)-1) if asks[i][1] > asks[i-1][1] and asks[i][1] > asks[i+1][1]][:3]
            support_str = ", ".join([price_format.format(price) for price in support_levels]) if support_levels else "未检测到"
            resistance_str = ", ".join([price_format.format(price) for price in resistance_levels]) if resistance_levels else "未检测到"

            bid_str = "\n".join([f"  - 价格: {price_format.format(price)}, 数量: {amount:.4f}" for price, amount in bids[:5]])
            ask_str = "\n".join([f"  - 价格: {price_format.format(price)}, 数量: {amount:.4f}" for price, amount in asks[:5]])
            
            await exchange_instance.close()
            
            display_output = (
                f"**{symbol} 在 {exchange} 的市场深度分析**\n\n"
                f"当前价格: {price_format.format(current_price)} USDT\n\n"
                f"**市场压力分析:**\n{pressure_analysis}\n\n"
                f"**潜在支撑位(USDT):** {support_str}\n"
                f"**潜在阻力位(USDT):** {resistance_str}\n\n"
                f"**买单前5档:**\n{bid_str}\n\n"
                f"**卖单前5档:**\n{ask_str}"
            )

            llm_feedback = (
                f"Market depth for {symbol}:\n"
                f"- Current Price: {price_format.format(current_price)} USDT\n"
                f"- Pressure: {pressure_analysis}\n"
                f"- Support: {support_str}\n"
                f"- Resistance: {resistance_str}"
            )

            return {"display": display_output, "llm_feedback": llm_feedback}

        except Exception as e:
            logger.error(f"Error fetching market depth for {symbol} on {exchange}: {str(e)}")
            error_msg = f"获取 {symbol} 在 {exchange} 的市场深度数据失败: {str(e)}"
            return {"display": error_msg, "llm_feedback": error_msg}
    @staticmethod
    async def get_top_movers( limit: int = 5,
                             exchange: str = "binance") -> dict:
        """
        Fetch the top movers (biggest price changes) on a specified exchange.
        Description: Retrieves a list of trading pairs with the highest percentage price changes over the last 24 hours.
        Type: Query
        Parameters:
            - limit (integer): Number of top movers to fetch (default: 5).
            - exchange (string): The exchange to query (default: binance).
        Return Value: A dictionary with 'display' for user and 'llm_feedback' for AI.
        Invocation: {"tool_name": "get_top_movers", "parameters": {"limit": 5, "exchange": "binance"}}
        """
        try:
            exchange_class = getattr(ccxt, exchange.lower(), None)
            if not exchange_class:
                error_msg = f"Unsupported exchange: {exchange}. Supported exchanges include 'binance', 'bybit', 'okx', 'gateio', etc."
                return {"display": error_msg, "llm_feedback": error_msg}

            exchange_instance = exchange_class({'enableRateLimit': True})
            tickers = await exchange_instance.fetch_tickers()
            
            futures_symbols = [s for s in tickers.keys() if ':USDT' in s]
            
            target_tickers = tickers
            if futures_symbols:
                target_tickers = {s: d for s, d in tickers.items() if s in futures_symbols}

            movers = sorted(
                [(s, d['percentage']) for s, d in target_tickers.items() if d.get('percentage') is not None],
                key=lambda x: abs(x[1]),
                reverse=True
            )[:limit]
            
            await exchange_instance.close()
            
            mover_str = "\n".join([f"  - {symbol}: {pct}% change" for symbol, pct in movers])
            contract_type = "永续合约" if futures_symbols else "现货"
            result_str = f"Top {limit} movers on {exchange} (24h percentage change, {contract_type}):\n{mover_str}"
            
            return {"display": result_str, "llm_feedback": result_str}

        except Exception as e:
            logger.error(f"Error fetching top movers on {exchange}: {str(e)}")
            error_msg = f"Failed to fetch top movers on {exchange}: {str(e)}"
            return {"display": error_msg, "llm_feedback": error_msg}
    @staticmethod
    async def get_candlestick_data(symbol: str = "BTC/USDT",
                                   timeframe: str = "1h", limit: int = 50, exchange: str = "binance") -> dict:
        """
        Fetch raw candlestick (OHLCV) data for a cryptocurrency pair.
        Description: Retrieves raw Open, High, Low, Close, and Volume data for a given trading pair, suitable for charting or custom analysis.
        Type: Query
        Parameters:
            - symbol (string): The trading pair symbol (e.g., BTC/USDT).
            - timeframe (string): The timeframe for candles (e.g., 1m, 5m, 1h, 1d).
            - limit (integer): Number of candles to fetch (default: 50).
            - exchange (string): The exchange to query (default: binance).
        Return Value: A dictionary with 'display' for user and 'llm_feedback' for AI.
        Invocation: {"tool_name": "get_candlestick_data", "parameters": {"symbol": "BTC/USDT", "timeframe": "1h", "limit": 50, "exchange": "binance"}}
        """
        try:
            exchange_class = getattr(ccxt, exchange.lower(), None)
            if not exchange_class:
                error_msg = f"Unsupported exchange: {exchange}. Supported exchanges include 'binance', 'bybit', 'okx', 'gateio', etc."
                return {"display": error_msg, "llm_feedback": error_msg}

            exchange_instance = exchange_class({'enableRateLimit': True})
            
            try_symbol = symbol
            if '/USDT' in symbol and not symbol.endswith(':USDT'):
                base_symbol = symbol.split('/')[0]
                try_symbol = f"{base_symbol}/USDT:USDT"
            
            try:
                ohlcv = await exchange_instance.fetch_ohlcv(try_symbol, timeframe, limit=limit)
                symbol = try_symbol
            except Exception:
                ohlcv = await exchange_instance.fetch_ohlcv(symbol, timeframe, limit=limit)
                
            if not ohlcv:
                error_msg = f"No candlestick data found for {symbol} on {exchange} with timeframe {timeframe}."
                return {"display": error_msg, "llm_feedback": error_msg}
                
            decimal_places = {j: 0 for j in range(1, 6)}
            for candle in ohlcv:
                for j in range(1, 6):
                    value_str = str(candle[j])
                    if '.' in value_str:
                        decimal_places[j] = max(decimal_places[j], len(value_str.split('.')[1]))
            
            display_limit = min(40, len(ohlcv))
            
            candlestick_str = "\n".join([
                f"  - Time: {datetime.datetime.fromtimestamp(candle[0]/1000)}, O: {candle[1]:.{decimal_places[1]}f}, "
                f"H: {candle[2]:.{decimal_places[2]}f}, L: {candle[3]:.{decimal_places[3]}f}, "
                f"C: {candle[4]:.{decimal_places[4]}f}, V: {candle[5]:.{decimal_places[5]}f}"
                for candle in ohlcv[-display_limit:]
            ])
            
            await exchange_instance.close()
            
            display_output = (
                f"Candlestick data for {symbol} on {exchange} (timeframe: {timeframe}, showing last {display_limit} of {len(ohlcv)} candles):\n"
                f"{candlestick_str}"
            )
            llm_feedback = f"Successfully fetched {len(ohlcv)} candlestick data points for {symbol}."

            return {"display": display_output, "llm_feedback": llm_feedback}

        except Exception as e:
            logger.error(f"Error fetching candlestick data for {symbol} on {exchange}: {str(e)}")
            error_msg = f"Failed to fetch candlestick data for {symbol} on {exchange}: {str(e)}"
            return {"display": error_msg, "llm_feedback": error_msg}
# Tool mapping for LLM invocation
MARKETTOOLS = {
    "get_coin_index": MarketTools.get_coin_index,  # 替换了多个工具
    "get_historical_data": MarketTools.get_historical_data,
    "get_market_depth": MarketTools.get_market_depth,
    "get_top_movers": MarketTools.get_top_movers,
    "get_candlestick_data": MarketTools.get_candlestick_data,
}




class DatabaseSuperTools:
    """A collection of super tools for direct database operations that can be invoked by an LLM."""
    
    @staticmethod
    async def query_db(command: str, params: str = "") -> dict:
        """
        Execute a database query operation and return the results.
        Description: Executes a SELECT query on the database and returns the results in a formatted string.
        Type: Query
        Parameters:
            - command (string): The SQL SELECT query to execute.
            - params (string): JSON string of parameters for the query (optional, default: "").
        Return Value: A dictionary with 'display' for user and 'llm_feedback' for AI.
        Invocation: {"tool_name": "query_db", "parameters": {"command": "SELECT * FROM users LIMIT 5", "params": ""}}
        """
        try:
            import json
            from typing import Tuple

            if params:
                try:
                    param_tuple = tuple(json.loads(params))
                except (json.JSONDecodeError, TypeError):
                    error_msg = f"Error: Invalid parameters format. Expected JSON array, got: {params}"
                    return {"display": error_msg, "llm_feedback": error_msg}
            else:
                param_tuple = ()

            result = db.query_db(command, param_tuple)

            if not result:
                msg = "Query executed successfully but returned no results."
                return {"display": msg, "llm_feedback": msg}

            # Format results for display (rich) and for LLM (concise)
            display_result = f"Command: \"{str(command)}\"\nParameters: {param_tuple}\nQuery Results:\n"
            llm_feedback_result = "Query Results:\n"
            
            for i, row in enumerate(result[:100]):
                row_str = f"Row {i+1}: {row}\n"
                display_result += row_str
                llm_feedback_result += row_str

            if len(result) > 100:
                trunc_msg = f"... and {len(result) - 100} more rows (truncated for display)"
                display_result += trunc_msg
                llm_feedback_result += trunc_msg

            return {"display": display_result, "llm_feedback": llm_feedback_result}

        except Exception as e:
            logger.error(f"Error executing database query: {str(e)}")
            error_msg = f"Database query failed: {str(e)}"
            return {"display": error_msg, "llm_feedback": error_msg}
    
    @staticmethod
    async def revise_db(command: str, params: str = "") -> dict:
        """
        Execute a database update operation and return the number of affected rows.
        Description: Executes an INSERT, UPDATE, or DELETE operation on the database.
        Type: Update
        Parameters:
            - command (string): The SQL command to execute (INSERT, UPDATE, DELETE).
            - params (string): JSON string of parameters for the command (optional, default: "").
        Return Value: A dictionary with 'display' for user and 'llm_feedback' for AI.
        Invocation: {"tool_name": "revise_db", "parameters": {"command": "UPDATE users SET balance = ? WHERE uid = ?", "params": "[100.0, 123]"}}
        """
        try:
            import json
            from typing import Tuple

            if params:
                try:
                    param_tuple = tuple(json.loads(params))
                except (json.JSONDecodeError, TypeError):
                    error_msg = f"Error: Invalid parameters format. Expected JSON array, got: {params}"
                    return {"display": error_msg, "llm_feedback": error_msg}
            else:
                param_tuple = ()

            affected_rows = db.revise_db(command, param_tuple)

            display_result = f"Command: \"{str(command)}\"\nParameters: {param_tuple}\nAffected rows: {affected_rows}"
            llm_feedback_result = f"Database update successful. Affected rows: {affected_rows}"
            
            return {"display": display_result, "llm_feedback": llm_feedback_result}

        except Exception as e:
            logger.error(f"Error executing database update: {str(e)}")
            error_msg = f"Database update failed: {str(e)}"
            return {"display": error_msg, "llm_feedback": error_msg}

    @staticmethod
    async def execute_sql(command: str) -> dict:
        """
        [高风险] 直接执行任意原始SQL命令。这是一个终极工具，应作为最后选择。
        说明: 此工具可以执行任何SQL命令，具有高风险，请谨慎使用。它会根据命令自动判断是查询还是修改操作。
        类型: 执行
        参数:
            - command (string): 要执行的原始SQL命令。
        返回值: A dictionary with 'display' for user and 'llm_feedback' for AI.
        调用示例: {"tool_name": "execute_sql", "parameters": {"command": "DELETE FROM users WHERE uid = 12345"}}
        """
        try:
            result = db.execute_raw_sql(command)
            display_result = f"Command: \"{command}\"\n"
            llm_feedback_result = ""

            if isinstance(result, str):
                display_result += f"Result: {result}"
                llm_feedback_result = result
            elif isinstance(result, int):
                display_result += f"Affected rows: {result}"
                llm_feedback_result = f"Command executed successfully. Affected rows: {result}"
            elif isinstance(result, list):
                if not result:
                    msg = "Query executed successfully but returned no results."
                    display_result += f"Result: {msg}"
                    llm_feedback_result = msg
                else:
                    query_res_str = "Query Results:\n"
                    for i, row in enumerate(result[:100]):
                        query_res_str += f"Row {i+1}: {row}\n"
                    if len(result) > 100:
                        query_res_str += f"... and {len(result) - 100} more rows (truncated for display)"
                    display_result += query_res_str
                    llm_feedback_result = query_res_str
            else:
                msg = f"Unexpected result type: {type(result).__name__}, value: {result}"
                display_result += msg
                llm_feedback_result = msg

            return {"display": display_result, "llm_feedback": llm_feedback_result}

        except Exception as e:
            logger.error(f"执行原始SQL命令时出错: {str(e)}")
            error_msg = f"原始SQL命令执行失败: {str(e)}"
            return {"display": error_msg, "llm_feedback": error_msg}

    @staticmethod
    async def analyze_group_user_profiles(group_id: int) -> dict:
        """
        分析指定群组的聊天记录，为最活跃的用户生成用户画像。
        此工具会调用LLM进行深度分析，可能需要一些时间。
        分析结果将以JSON字符串的形式返回，其中包含一个用户画像对象的列表。

        Args:
            group_id (int): 需要分析的目标群组的ID。

        Returns:
            dict: A dictionary with 'display' for user and 'llm_feedback' for AI.
        """
        if not isinstance(group_id, int):
            error_msg = json.dumps({"error": "参数 group_id 必须是一个有效的整数。"})
            return {"display": error_msg, "llm_feedback": error_msg}
            
        # 调用在 llm_functions.py 中定义的核心函数
        from agent.llm_functions import generate_user_profile as gup
        result_json_str = await gup(group_id)
        
        # For this tool, the result is a JSON string that is useful for both user and LLM.
        return {"display": result_json_str, "llm_feedback": result_json_str}


# Tool mapping for LLM invocation
DATABASE_SUPER_TOOLS = {
    "query_db": DatabaseSuperTools.query_db,
    "revise_db": DatabaseSuperTools.revise_db,
    "analyze_group_user_profiles": DatabaseSuperTools.analyze_group_user_profiles,
    "execute_sql": DatabaseSuperTools.execute_sql,
}
