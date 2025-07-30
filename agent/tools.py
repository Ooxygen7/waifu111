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
                return f"Unsupported exchange: {exchange}. Supported exchanges include 'binance', 'bybit', 'okx', 'gateio', etc."
            exchange_instance = exchange_class({'enableRateLimit': True})
            
            # 尝试获取永续合约数据
            try_symbol = symbol
            if '/USDT' in symbol and not symbol.endswith(':USDT'):
                # 尝试将现货符号转换为永续合约符号
                base_symbol = symbol.split('/')[0]
                try_symbol = f"{base_symbol}/USDT:USDT"
            
            try:
                # 尝试获取永续合约数据
                ohlcv = await exchange_instance.fetch_ohlcv(try_symbol, timeframe, limit=limit)
                symbol = try_symbol  # 如果成功，更新使用的符号
            except Exception:
                # 如果永续合约获取失败，回退到原始符号
                ohlcv = await exchange_instance.fetch_ohlcv(symbol, timeframe, limit=limit)
                
            if not ohlcv:
                return f"No historical data found for {symbol} on {exchange} with timeframe {timeframe}."
                
            closes = np.array([candle[4] for candle in ohlcv])
            volumes = [candle[5] for candle in ohlcv]
            
            # 确定价格和交易量的小数位数
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
            
            # 使用动态格式化字符串保持原始精度
            price_format = f"{{:.{price_decimal_places}f}}"
            volume_format = f"{{:.{volume_decimal_places}f}}"
            
            # Current Price
            current_price = closes[-1]
            
            # Market Trends
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
                sma_result = f"{price_format.format(sma)} USDT, current price is {sma_trend}"
            
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
                macd_result = f"MACD={price_format.format(current_macd)}, Signal={price_format.format(current_signal)} ({macd_interpretation})" if macd_interpretation else f"MACD={price_format.format(current_macd)}, Signal={price_format.format(current_signal)}"
            
            await exchange_instance.close()
            return (
                f"**Coin Index Analysis for {symbol} on {exchange} (timeframe: {timeframe}, limit: {limit}):**\n"
                f"- Current Price: {price_format.format(current_price)} USDT\n"
                f"- Market Trend: {trend.capitalize()} - {trend_desc}\n"
                f"- Volume Analysis: Avg={volume_format.format(avg_volume)}, High={volume_format.format(max_volume)}, Low={volume_format.format(min_volume)}, Recent={volume_format.format(recent_volume)} ({volume_trend})\n"
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
                return f"Unsupported exchange: {exchange}. Supported exchanges include 'binance', 'bybit', 'okx', 'gateio', etc."
            exchange_instance = exchange_class({'enableRateLimit': True})
            
            # 尝试获取永续合约数据
            try_symbol = symbol
            if '/USDT' in symbol and not symbol.endswith(':USDT'):
                # 尝试将现货符号转换为永续合约符号
                base_symbol = symbol.split('/')[0]
                try_symbol = f"{base_symbol}/USDT:USDT"
            
            try:
                # 尝试获取永续合约数据
                ohlcv = await exchange_instance.fetch_ohlcv(try_symbol, timeframe, limit=limit)
                symbol = try_symbol  # 如果成功，更新使用的符号
            except Exception:
                # 如果永续合约获取失败，回退到原始符号
                ohlcv = await exchange_instance.fetch_ohlcv(symbol, timeframe, limit=limit)
                
            if not ohlcv:
                return f"No historical data found for {symbol} on {exchange} with timeframe {timeframe}."
                
            closes = [candle[4] for candle in ohlcv]
            avg_price = sum(closes) / len(closes)
            max_price = max(closes)
            min_price = min(closes)
            
            # 确定价格的小数位数
            decimal_places = 0
            if closes:
                # 检查第一个收盘价的字符串表示，确定小数位数
                price_str = str(closes[0])
                if '.' in price_str:
                    decimal_places = len(price_str.split('.')[1])
            
            # 使用动态格式化字符串保持原始精度
            format_str = f"{{:.{decimal_places}f}}"
            
            await exchange_instance.close()
            return (
                f"Historical data for {symbol} on {exchange} (timeframe: {timeframe}, last {limit} candles):\n"
                f"- Average Close Price: {format_str.format(avg_price)} USDT\n"
                f"- Highest Close Price: {format_str.format(max_price)} USDT\n"
                f"- Lowest Close Price: {format_str.format(min_price)} USDT"
            )
        except Exception as e:
            logger.error(f"Error fetching historical data for {symbol} on {exchange}: {str(e)}")
            return f"Failed to fetch historical data for {symbol} on {exchange}: {str(e)}"
    @staticmethod
    async def get_market_depth(symbol: str = "BTC/USDT",
                             depth: int = 10, exchange: str = "binance") -> str:
        """
        Fetch the market depth data for a cryptocurrency pair.
        Description: Retrieves detailed order book depth data showing buy/sell pressure at different price levels.
        Type: Query
        Parameters:
            - symbol (string): The trading pair symbol (e.g., BTC/USDT).
            - depth (integer): Depth of order book to analyze (default: 10).
            - exchange (string): The exchange to query (default: binance).
        Return Value: A string summarizing the market depth with buy/sell pressure analysis.
        Invocation: {"tool_name": "get_market_depth", "parameters": {"symbol": "BTC/USDT", "depth": 10, "exchange": "binance"}}
        """
        try:
            exchange_class = getattr(ccxt, exchange.lower(), None)
            if not exchange_class:
                return f"Unsupported exchange: {exchange}. Supported exchanges include 'binance', 'bybit', 'okx', 'gateio', etc."
            exchange_instance = exchange_class({'enableRateLimit': True})
            
            # 尝试获取永续合约数据
            try_symbol = symbol
            if '/USDT' in symbol and not symbol.endswith(':USDT'):
                # 尝试将现货符号转换为永续合约符号
                base_symbol = symbol.split('/')[0]
                try_symbol = f"{base_symbol}/USDT:USDT"
            
            try:
                # 尝试获取永续合约订单簿
                order_book = await exchange_instance.fetch_order_book(try_symbol, limit=depth*5)  # 获取更多数据以便分析
                symbol = try_symbol  # 如果成功，更新使用的符号
            except Exception:
                # 如果永续合约获取失败，回退到原始符号
                order_book = await exchange_instance.fetch_order_book(symbol, limit=depth*5)
            
            # 获取当前价格（中间价）
            if len(order_book.get('bids', [])) > 0 and len(order_book.get('asks', [])) > 0:
                current_price = (order_book['bids'][0][0] + order_book['asks'][0][0]) / 2
            elif len(order_book.get('bids', [])) > 0:
                current_price = order_book['bids'][0][0]
            elif len(order_book.get('asks', [])) > 0:
                current_price = order_book['asks'][0][0]
            else:
                current_price = 0
            
            # 计算买卖压力
            bids = order_book.get('bids', [])
            asks = order_book.get('asks', [])
            
            # 计算累计量和价格区间
            bid_levels = []
            ask_levels = []
            
            # 处理买单（按价格降序）
            total_bid_volume = 0
            for i, (price, amount) in enumerate(bids[:depth]):
                total_bid_volume += amount
                bid_levels.append({
                    "price": price,
                    "amount": amount,
                    "cumulative": total_bid_volume,
                    "distance": ((current_price - price) / current_price) * 100  # 距离当前价格的百分比
                })
            
            # 处理卖单（按价格升序）
            total_ask_volume = 0
            for i, (price, amount) in enumerate(asks[:depth]):
                total_ask_volume += amount
                ask_levels.append({
                    "price": price,
                    "amount": amount,
                    "cumulative": total_ask_volume,
                    "distance": ((price - current_price) / current_price) * 100  # 距离当前价格的百分比
                })
            
            # 计算买卖压力比率
            buy_sell_ratio = total_bid_volume / total_ask_volume if total_ask_volume > 0 else float('inf')
            
            # 分析市场深度，使用中文输出
            if buy_sell_ratio > 1.5:
                pressure_analysis = f"强烈买入压力 (买/卖比率: {buy_sell_ratio:.2f})"
            elif buy_sell_ratio < 0.67:
                pressure_analysis = f"强烈卖出压力 (买/卖比率: {buy_sell_ratio:.2f})"
            else:
                pressure_analysis = f"买卖压力平衡 (买/卖比率: {buy_sell_ratio:.2f})"
            
            # 分析价格支撑/阻力位
            support_levels = []
            resistance_levels = []
            
            # 寻找支撑位（买单集中的价格区间）
            for i in range(1, len(bid_levels)-1):
                if bid_levels[i]["amount"] > bid_levels[i-1]["amount"] and bid_levels[i]["amount"] > bid_levels[i+1]["amount"]:
                    support_levels.append(bid_levels[i]["price"])
            
            # 寻找阻力位（卖单集中的价格区间）
            for i in range(1, len(ask_levels)-1):
                if ask_levels[i]["amount"] > ask_levels[i-1]["amount"] and ask_levels[i]["amount"] > ask_levels[i+1]["amount"]:
                    resistance_levels.append(ask_levels[i]["price"])
            
            # 限制支撑/阻力位数量
            support_levels = support_levels[:3]
            resistance_levels = resistance_levels[:3]
            
            # 格式化输出
            # 确定价格的小数位数
            decimal_places = 0
            if bids:
                price_str = str(bids[0][0])
                if '.' in price_str:
                    decimal_places = len(price_str.split('.')[1])
            
            # 使用动态格式化字符串保持原始精度
            price_format = f"{{:.{decimal_places}f}}"
            
            # 合并深度数据到5档，减少返回内容长度
            merged_bids = []
            merged_asks = []
            
            # 如果深度大于5，则合并为5档
            if len(bid_levels) > 5:
                # 计算每档的平均值
                for i in range(5):
                    start_idx = i * (len(bid_levels) // 5)
                    end_idx = (i + 1) * (len(bid_levels) // 5) if i < 4 else len(bid_levels)
                    
                    avg_price = sum(level['price'] for level in bid_levels[start_idx:end_idx]) / (end_idx - start_idx)
                    total_amount = sum(level['amount'] for level in bid_levels[start_idx:end_idx])
                    avg_distance = sum(level['distance'] for level in bid_levels[start_idx:end_idx]) / (end_idx - start_idx)
                    cumulative = bid_levels[end_idx-1]['cumulative'] if end_idx > 0 and end_idx <= len(bid_levels) else 0
                    
                    merged_bids.append({
                        "price": avg_price,
                        "amount": total_amount,
                        "cumulative": cumulative,
                        "distance": avg_distance
                    })
            else:
                merged_bids = bid_levels
            
            # 同样处理卖单
            if len(ask_levels) > 5:
                for i in range(5):
                    start_idx = i * (len(ask_levels) // 5)
                    end_idx = (i + 1) * (len(ask_levels) // 5) if i < 4 else len(ask_levels)
                    
                    avg_price = sum(level['price'] for level in ask_levels[start_idx:end_idx]) / (end_idx - start_idx)
                    total_amount = sum(level['amount'] for level in ask_levels[start_idx:end_idx])
                    avg_distance = sum(level['distance'] for level in ask_levels[start_idx:end_idx]) / (end_idx - start_idx)
                    cumulative = ask_levels[end_idx-1]['cumulative'] if end_idx > 0 and end_idx <= len(ask_levels) else 0
                    
                    merged_asks.append({
                        "price": avg_price,
                        "amount": total_amount,
                        "cumulative": cumulative,
                        "distance": avg_distance
                    })
            else:
                merged_asks = ask_levels
            
            # 格式化合并后的买单和卖单信息
            bid_str = "\n".join([f"  - 价格区间: {price_format.format(level['price'])} USDT, 总量: {level['amount']:.4f}, 累计: {level['cumulative']:.4f}, 距当前价: {level['distance']:.2f}%" 
                                for level in merged_bids])
            ask_str = "\n".join([f"  - 价格区间: {price_format.format(level['price'])} USDT, 总量: {level['amount']:.4f}, 累计: {level['cumulative']:.4f}, 距当前价: {level['distance']:.2f}%" 
                                for level in merged_asks])
            
            # 格式化支撑位和阻力位，使用中文输出
            support_str = ", ".join([price_format.format(price) for price in support_levels]) if support_levels else "未检测到"
            resistance_str = ", ".join([price_format.format(price) for price in resistance_levels]) if resistance_levels else "未检测到"
            
            await exchange_instance.close()
            
            # 简化输出格式，使用中文，减少内容长度
            return (
                f"**{symbol} 在 {exchange} 的市场深度分析**\n\n"
                f"当前价格: {price_format.format(current_price)} USDT\n\n"
                f"**市场压力分析:**\n{pressure_analysis}\n\n"
                f"**潜在支撑位(USDT):** {support_str}\n"
                f"**潜在阻力位(USDT):** {resistance_str}\n\n"
                f"**买单(合并5档):**\n{bid_str}\n\n"
                f"**卖单(合并5档):**\n{ask_str}"
            )
        except Exception as e:
            logger.error(f"Error fetching market depth for {symbol} on {exchange}: {str(e)}")
            return f"获取 {symbol} 在 {exchange} 的市场深度数据失败: {str(e)}"
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
                return f"Unsupported exchange: {exchange}. Supported exchanges include 'binance', 'bybit', 'okx', 'gateio', etc."
            exchange_instance = exchange_class({'enableRateLimit': True})
            tickers = await exchange_instance.fetch_tickers()
            
            # 优先考虑永续合约
            futures_symbols = [symbol for symbol in tickers.keys() if ':USDT' in symbol]
            
            # 如果有永续合约，优先使用永续合约数据
            if futures_symbols:
                # 过滤只保留永续合约数据
                futures_tickers = {symbol: data for symbol, data in tickers.items() if symbol in futures_symbols}
                movers = sorted(
                    [(symbol, data['percentage']) for symbol, data in futures_tickers.items() if
                     'percentage' in data and data['percentage'] is not None],
                    key=lambda x: abs(x[1]),
                    reverse=True
                )[:limit]
            else:
                # 如果没有永续合约，使用所有数据
                movers = sorted(
                    [(symbol, data['percentage']) for symbol, data in tickers.items() if
                     'percentage' in data and data['percentage'] is not None],
                    key=lambda x: abs(x[1]),
                    reverse=True
                )[:limit]
            
            await exchange_instance.close()
            
            # 保持原始精度输出百分比变化
            mover_str = "\n".join([f"  - {symbol}: {pct}% change" for symbol, pct in movers])
            
            # 添加说明是否使用了永续合约数据
            contract_type = "永续合约" if futures_symbols else "现货"
            return f"Top {limit} movers on {exchange} (24h percentage change, {contract_type}):\n{mover_str}"
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
                return f"Unsupported exchange: {exchange}. Supported exchanges include 'binance', 'bybit', 'okx', 'gateio', etc."
            exchange_instance = exchange_class({'enableRateLimit': True})
            
            # 尝试获取永续合约数据
            try_symbol = symbol
            if '/USDT' in symbol and not symbol.endswith(':USDT'):
                # 尝试将现货符号转换为永续合约符号
                base_symbol = symbol.split('/')[0]
                try_symbol = f"{base_symbol}/USDT:USDT"
            
            try:
                # 尝试获取永续合约数据
                ohlcv = await exchange_instance.fetch_ohlcv(try_symbol, timeframe, limit=limit)
                symbol = try_symbol  # 如果成功，更新使用的符号
            except Exception:
                # 如果永续合约获取失败，回退到原始符号
                ohlcv = await exchange_instance.fetch_ohlcv(symbol, timeframe, limit=limit)
                
            if not ohlcv:
                return f"No candlestick data found for {symbol} on {exchange} with timeframe {timeframe}."
                
            # 确定价格的小数位数
            decimal_places = {}
            for i, candle in enumerate(ohlcv):
                for j in range(1, 6):  # 检查开盘、最高、最低、收盘价和交易量
                    if j not in decimal_places:
                        decimal_places[j] = 0
                    # 检查数字的字符串表示，确定小数位数
                    value_str = str(candle[j])
                    if '.' in value_str:
                        dp = len(value_str.split('.')[1])
                        decimal_places[j] = max(decimal_places[j], dp)
            
            # 限制返回的条目数，避免输出过长，仅展示最新的几条数据
            display_limit = min(40, len(ohlcv))
            
            # 使用动态格式化字符串保持原始精度
            candlestick_str = "\n".join([
                f"  - Time: {candle[0]}, Open: {candle[1]:.{decimal_places.get(1, 2)}f}, "
                f"High: {candle[2]:.{decimal_places.get(2, 2)}f}, Low: {candle[3]:.{decimal_places.get(3, 2)}f}, "
                f"Close: {candle[4]:.{decimal_places.get(4, 2)}f}, Volume: {candle[5]:.{decimal_places.get(5, 2)}f}"
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
    "get_market_depth": MarketTools.get_market_depth,
    "get_top_movers": MarketTools.get_top_movers,
    "get_candlestick_data": MarketTools.get_candlestick_data,
}




class DatabaseSuperTools:
    """A collection of super tools for direct database operations that can be invoked by an LLM."""
    
    @staticmethod
    async def query_db(command: str, params: str = "") -> str:
        """
        Execute a database query operation and return the results.
        Description: Executes a SELECT query on the database and returns the results in a formatted string.
        Type: Query
        Parameters:
            - command (string): The SQL SELECT query to execute.
            - params (string): JSON string of parameters for the query (optional, default: "").
        Return Value: A string containing the query results or error message.
        Invocation: {"tool_name": "query_db", "parameters": {"command": "SELECT * FROM users LIMIT 5", "params": ""}}
        """
        try:
            import json
            from typing import Tuple
            
            # Parse parameters if provided
            if params:
                try:
                    param_tuple = tuple(json.loads(params))
                except (json.JSONDecodeError, TypeError):
                    return f"Error: Invalid parameters format. Expected JSON array, got: {params}"
            else:
                param_tuple = ()
            
            # Execute query
            result = db.query_db(command, param_tuple)
            
            if not result:
                return "Query executed successfully but returned no results."
            
            # Format results
            formatted_result = f"Command\"{str(command)}\"\nQuery Results:\n"
            for i, row in enumerate(result[:100]):  # Limit to 100 rows for readability
                formatted_result += f"Row {i+1}: {row}\n"
            
            if len(result) > 100:
                formatted_result += f"... and {len(result) - 100} more rows (truncated for display)"
            
            return formatted_result
            
        except Exception as e:
            logger.error(f"Error executing database query: {str(e)}")
            return f"Database query failed: {str(e)}"
    
    @staticmethod
    async def revise_db(command: str, params: str = "") -> str:
        """
        Execute a database update operation and return the number of affected rows.
        Description: Executes an INSERT, UPDATE, or DELETE operation on the database.
        Type: Update
        Parameters:
            - command (string): The SQL command to execute (INSERT, UPDATE, DELETE).
            - params (string): JSON string of parameters for the command (optional, default: "").
        Return Value: A string indicating the number of affected rows or error message.
        Invocation: {"tool_name": "revise_db", "parameters": {"command": "UPDATE users SET balance = ? WHERE uid = ?", "params": "[100.0, 123]"}}
        """
        try:
            import json
            from typing import Tuple
            
            # Parse parameters if provided
            if params:
                try:
                    param_tuple = tuple(json.loads(params))
                except (json.JSONDecodeError, TypeError):
                    return f"Error: Invalid parameters format. Expected JSON array, got: {params}"
            else:
                param_tuple = ()
            
            # Execute update
            affected_rows = db.revise_db(command, param_tuple)
            
            return f"Command\"{str(command)}\"\nAffected rows: {affected_rows}"
            
        except Exception as e:
            logger.error(f"Error executing database update: {str(e)}")
            return f"Database update failed: {str(e)}"


# Tool mapping for LLM invocation
DATABASE_SUPER_TOOLS = {
    "query_db": DatabaseSuperTools.query_db,
    "revise_db": DatabaseSuperTools.revise_db,
}
