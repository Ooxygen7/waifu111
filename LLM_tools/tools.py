"""
toolsprivate.py - Private command tools for LLM interaction.

This module provides a set of tools that can be invoked by an LLM to interact with
the CyberWaifu bot system. Each tool corresponds to a private command that can be
executed in a user's private chat context.
"""

import datetime
import os
import logging
from typing import Optional

from telegram import Update
from telegram.ext import ContextTypes

import bot_core.public_functions.update_parse as public
from bot_core.callback_handlers.inline import Inline
from utils import db_utils as db
from utils.logging_utils import setup_logging

setup_logging()
logger = logging.getLogger(__name__)


class PrivateTools:
    """A collection of tools for private commands that can be invoked by an LLM."""

    @staticmethod
    async def stream(update: Update, context: ContextTypes.DEFAULT_TYPE) -> str:
        """
        Toggle streaming mode for message delivery.

        Description: Switches between streaming and non-streaming mode for message delivery.
        Type: Operation
        Parameters: None
        Return Value: A string indicating whether streaming mode was toggled successfully.
        Invocation: {"tool_name": "stream", "parameters": {}}
        """
        info = public.update_info_get(update)
        if db.user_stream_switch(info['user_id']):
            await update.message.reply_text("切换成功！")
            return "Streaming mode toggled successfully."
        return "Failed to toggle streaming mode."

    @staticmethod
    async def me(update: Update, context: ContextTypes.DEFAULT_TYPE) -> str:
        """
        Display the user's personal information, including account tier, quota, and balance.

        Description: Retrieves and returns user-specific information for analysis or display.
        Type: Query
        Parameters: None
        Return Value: A string containing user information.
        Invocation: {"tool_name": "me", "parameters": {}}
        """
        info = public.update_info_get(update)
        result = (
            f"用户名: {info['user_name']}, "
            f"账户等级: {info['tier']}, "
            f"剩余额度: {info['remain']}, "
            f"临时额度: {db.user_sign_info_get(info['user_id']).get('frequency')}, "
            f"余额: {info['balance']}, "
            f"对话昵称: {info['user_nick']}"
        )
        return result

    @staticmethod
    async def status(update: Update, context: ContextTypes.DEFAULT_TYPE) -> str:
        """
        Display the current settings, including character, API, preset, and streaming status.

        Description: Retrieves and returns the current configuration settings of the conversation.
        Type: Query
        Parameters: None
        Return Value: A string containing current settings.
        Invocation: {"tool_name": "status", "parameters": {}}
        """
        info = public.update_info_get(update)
        result = (
            f"当前角色: {info['char']}, "
            f"当前接口: {info['api']}, "
            f"当前预设: {info['preset']}, "
            f"流式传输: {info['stream']}"
        )
        return result

    @staticmethod
    async def newchar(update: Update, context: ContextTypes.DEFAULT_TYPE, char_name: Optional[str] = None) -> str:
        """
        Start the creation of a new character with a specified name.

        Description: Initiates the process of creating a new character with the provided name.
        Type: Operation
        Parameters:
            - char_name (string): The name of the new character to be created.
        Return Value: A string confirming the start of new character creation with the specified name.
        Invocation: {"tool_name": "newchar", "parameters": {"char_name": "Alice"}}
        """
        info = public.update_info_get(update)
        args = context.args if hasattr(context, 'args') else []
        if not char_name and (not args or len(args[0].strip()) == 0):
            await update.message.reply_text("请使用 /newchar char_name 的格式指定角色名。")
            return "Character name required."
        char_name = char_name or args[0].strip()
        if not hasattr(context.bot_data, 'newchar_state'):
            context.bot_data['newchar_state'] = {}
        context.bot_data['newchar_state'][info['user_id']] = {'char_name': char_name, 'desc_chunks': []}
        await update.message.reply_text(
            f"请上传角色描述文件（json/txt）或直接发送文本描述，完成后发送 /done 结束输入。\n如描述较长可分多条消息发送。")
        return f"New character creation started for {char_name}."

    @staticmethod
    async def nick(update: Update, context: ContextTypes.DEFAULT_TYPE, nickname: Optional[str] = None) -> str:
        """
        Set a nickname for the user in conversations.

        Description: Updates the user's nickname for use in conversations.
        Type: Operation
        Parameters:
            - nickname (string): The nickname to set for the user.
        Return Value: A string confirming the nickname update or indicating failure.
        Invocation: {"tool_name": "nick", "parameters": {"nickname": "CrispShark"}}
        """
        info = public.update_info_get(update)
        args = context.args if hasattr(context, 'args') else []
        if not nickname and (not args or len(args[0].strip()) == 0):
            await update.message.reply_text("请使用 /nick nickname 的格式指定昵称。如：/nick 脆脆鲨")
            return "Nickname required."
        nick_name = nickname or args[0].strip()
        if db.user_config_arg_update(info['user_id'], 'nick', nick_name):
            # await update.message.reply_text(f"昵称已更新为：{nick_name}")
            return f"Nickname updated to {nick_name}."
        else:
            # await update.message.reply_text(f"昵称更新失败")
            return "Failed to update nickname."

    @staticmethod
    async def delete(update: Update, context: ContextTypes.DEFAULT_TYPE) -> str:
        """
        Prompt the user to delete a saved conversation.

        Description: Displays a list of saved conversations for the user to delete.
        Type: Operation
        Parameters: None
        Return Value: A string confirming that conversation deletion selection has been prompted.
        Invocation: {"tool_name": "delete", "parameters": {}}
        """
        info = public.update_info_get(update)
        markup = Inline.print_conversations(info['user_id'], 'delete')
        if markup == "没有可用的对话。":
            await update.message.reply_text(markup)
        else:
            await update.message.reply_text("请选择一个对话：", reply_markup=markup)
        await update.message.delete()
        return "Conversation deletion selection prompted."

    @staticmethod
    async def sign(update: Update, context: ContextTypes.DEFAULT_TYPE) -> str:
        """
        Perform a daily check-in to gain temporary quota (limited to once every 8 hours).

        Description: Allows the user to check in daily to increase temporary quota.
        Type: Operation
        Parameters: None
        Return Value: A string indicating the result of the check-in (success or time restriction).
        Invocation: {"tool_name": "sign", "parameters": {}}
        """
        user_id = update.message.from_user.id
        sign_info = db.user_sign_info_get(user_id)
        if sign_info.get('last_sign') == 0:
            db.user_sign_info_create(user_id)
            sign_info = db.user_sign_info_get(user_id)
            # await update.message.reply_text(
            # f"签到成功！临时额度+50！\r\n你的临时额度为: {sign_info.get('frequency')}条(上限100)")
            return "Check-in successful, temporary quota increased by 50."
        else:
            concurrent_time = datetime.datetime.now()
            last_sign_time = datetime.datetime.strptime(sign_info.get('last_sign'), '%Y-%m-%d %H:%M:%S.%f')
            time_delta = concurrent_time - last_sign_time
            total_seconds = time_delta.total_seconds()
            if total_seconds < 28800:  # 8 hours = 28800 seconds
                remaining_hours = (28800 - total_seconds) // 3600
                # await update.message.reply_text(
                # f"您8小时内已完成过签到，您可以在{str(remaining_hours)}小时后再次签到。")
                return f"Check-in already done within 8 hours, retry after {remaining_hours} hours."
            else:
                db.user_sign(user_id)
                sign_info = db.user_sign_info_get(user_id)
                # await update.message.reply_text(
                # f"签到成功！临时额度+50！\r\n你的临时额度为: {sign_info.get('frequency')}条(上限100)")
                return "Check-in successful, temporary quota increased by 50."

    @staticmethod
    async def conv_info(update: Update, context: ContextTypes.DEFAULT_TYPE) -> str:
        info = public.update_info_get(update)


# Tool mapping for LLM invocation
PRIVATETOOLS = {
    "stream": PrivateTools.stream,
    "me": PrivateTools.me,
    "status": PrivateTools.status,
    "newchar": PrivateTools.newchar,
    "nick": PrivateTools.nick,
    "delete": PrivateTools.delete,
    "sign": PrivateTools.sign,
}
"""
tools_market.py - Market analysis tools for LLM interaction.

This module provides a set of tools that can be invoked by an LLM to perform cryptocurrency market analysis
using the CCXT library. These tools allow fetching market data, historical prices, technical indicators, and more.
"""

import logging
from typing import Optional, Dict, Any, List
import ccxt.async_support as ccxt  # 使用异步支持以兼容 Telegram 机器人
import pandas as pd  # 用于数据处理和技术指标计算
import numpy as np  # 用于数值计算
from telegram import Update
from telegram.ext import ContextTypes
from utils.logging_utils import setup_logging
import datetime

setup_logging()
logger = logging.getLogger(__name__)


class MarketTools:
    """A collection of tools for cryptocurrency market analysis that can be invoked by an LLM."""

    @staticmethod
    async def get_price(update: Update, context: ContextTypes.DEFAULT_TYPE, symbol: str = "BTC/USDT", exchange: str = "binance") -> str:
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
    async def get_historical_data(update: Update, context: ContextTypes.DEFAULT_TYPE, symbol: str = "BTC/USDT", timeframe: str = "1h", limit: int = 100, exchange: str = "binance") -> str:
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
    async def get_order_book(update: Update, context: ContextTypes.DEFAULT_TYPE, symbol: str = "BTC/USDT", limit: int = 10, exchange: str = "binance") -> str:
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
            bid_str = "\n".join([f"  - Bid: {price} USDT, Amount: {amount}" for price, amount in bids]) if bids else "No bids available."
            ask_str = "\n".join([f"  - Ask: {price} USDT, Amount: {amount}" for price, amount in asks]) if asks else "No asks available."
            return (
                f"Order book for {symbol} on {exchange} (top entries):\n"
                f"Bids (Buy Orders):\n{bid_str}\n"
                f"Asks (Sell Orders):\n{ask_str}"
            )
        except Exception as e:
            logger.error(f"Error fetching order book for {symbol} on {exchange}: {str(e)}")
            return f"Failed to fetch order book for {symbol} on {exchange}: {str(e)}"

    @staticmethod
    async def get_market_trends(update: Update, context: ContextTypes.DEFAULT_TYPE, symbol: str = "BTC/USDT", timeframe: str = "1d", limit: int = 30, exchange: str = "binance") -> str:
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
    async def get_volume_analysis(update: Update, context: ContextTypes.DEFAULT_TYPE, symbol: str = "BTC/USDT", timeframe: str = "1h", limit: int = 50, exchange: str = "binance") -> str:
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
    async def get_rsi(update: Update, context: ContextTypes.DEFAULT_TYPE, symbol: str = "BTC/USDT", timeframe: str = "1h", limit: int = 50, period: int = 14, exchange: str = "binance") -> str:
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
    async def get_moving_average(update: Update, context: ContextTypes.DEFAULT_TYPE, symbol: str = "BTC/USDT", timeframe: str = "1h", limit: int = 50, period: int = 20, exchange: str = "binance") -> str:
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
    async def get_macd(update: Update, context: ContextTypes.DEFAULT_TYPE, symbol: str = "BTC/USDT", timeframe: str = "1h", limit: int = 50, exchange: str = "binance") -> str:
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
    async def get_support_resistance(update: Update, context: ContextTypes.DEFAULT_TYPE, symbol: str = "BTC/USDT", timeframe: str = "1h", limit: int = 100, exchange: str = "binance") -> str:
        """
        Identify support and resistance levels for a cryptocurrency pair.

        Description: Analyzes historical data to estimate key support and resistance price levels.
        Type: Analysis
        Parameters:
            - symbol (string): The trading pair symbol (e.g., BTC/USDT).
            - timeframe (string): The timeframe for analysis (e.g., 1h, 1d).
            - limit (integer): Number of historical data points to analyze (default: 100).
            - exchange (string): The exchange to query (default: binance).
        Return Value: A string summarizing the identified support and resistance levels.
        Invocation: {"tool_name": "get_support_resistance", "parameters": {"symbol": "BTC/USDT", "timeframe": "1h", "limit": 100, "exchange": "binance"}}
        """
        try:
            exchange_class = getattr(ccxt, exchange.lower(), None)
            if not exchange_class:
                return f"Unsupported exchange: {exchange}. Supported exchanges include 'binance', 'coinbase', etc."
            exchange_instance = exchange_class({'enableRateLimit': True})
            ohlcv = await exchange_instance.fetch_ohlcv(symbol, timeframe, limit=limit)
            if not ohlcv:
                return f"No historical data found for {symbol} on {exchange} with timeframe {timeframe}."
            highs = [candle[2] for candle in ohlcv]  # High prices
            lows = [candle[3] for candle in ohlcv]   # Low prices
            # 简单估计：支持位取最低价前5%的平均值，阻力位取最高价前5%的平均值
            sorted_lows = sorted(lows)
            sorted_highs = sorted(highs, reverse=True)
            support = sum(sorted_lows[:int(len(sorted_lows) * 0.05)]) / (int(len(sorted_lows) * 0.05) or 1)
            resistance = sum(sorted_highs[:int(len(sorted_highs) * 0.05)]) / (int(len(sorted_highs) * 0.05) or 1)
            await exchange_instance.close()
            return (
                f"Support and Resistance levels for {symbol} on {exchange} (timeframe: {timeframe}):\n"
                f"- Estimated Support: {support:.2f} USDT\n"
                f"- Estimated Resistance: {resistance:.2f} USDT"
            )
        except Exception as e:
            logger.error(f"Error calculating support/resistance for {symbol} on {exchange}: {str(e)}")
            return f"Failed to calculate support/resistance for {symbol} on {exchange}: {str(e)}"

    @staticmethod
    async def get_top_movers(update: Update, context: ContextTypes.DEFAULT_TYPE, limit: int = 5, exchange: str = "binance") -> str:
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
                [(symbol, data['percentage']) for symbol, data in tickers.items() if 'percentage' in data and data['percentage'] is not None],
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
    async def get_funding_rate(update: Update, context: ContextTypes.DEFAULT_TYPE, symbol: str = "BTC/USDT", exchange: str = "binance") -> str:
        """
        Fetch the current funding rate for a cryptocurrency futures pair.

        Description: Retrieves the funding rate for perpetual futures contracts, indicating market sentiment.
        Type: Query
        Parameters:
            - symbol (string): The trading pair symbol (e.g., BTC/USDT).
            - exchange (string): The exchange to query (default: binance).
        Return Value: A string summarizing the funding rate and its implication.
        Invocation: {"tool_name": "get_funding_rate", "parameters": {"symbol": "BTC/USDT", "exchange": "binance"}}
        """
        try:
            exchange_class = getattr(ccxt, exchange.lower(), None)
            if not exchange_class:
                return f"Unsupported exchange: {exchange}. Supported exchanges include 'binance', 'coinbase', etc."
            exchange_instance = exchange_class({'enableRateLimit': True})
            funding_rate = await exchange_instance.fetch_funding_rate(symbol)
            rate = funding_rate.get('fundingRate', 0)
            sentiment = (
                "Bullish (longs pay shorts)" if rate > 0 else
                "Bearish (shorts pay longs)" if rate < 0 else
                "Neutral"
            )
            await exchange_instance.close()
            return f"Funding rate for {symbol} on {exchange}: {rate:.4f} ({sentiment})"
        except Exception as e:
            logger.error(f"Error fetching funding rate for {symbol} on {exchange}: {str(e)}")
            return f"Failed to fetch funding rate for {symbol} on {exchange}: {str(e)}"

    @staticmethod
    async def get_volatility(update: Update, context: ContextTypes.DEFAULT_TYPE, symbol: str = "BTC/USDT", timeframe: str = "1h", limit: int = 50, exchange: str = "binance") -> str:
        """
        Calculate price volatility for a cryptocurrency pair based on historical data.

        Description: Computes the standard deviation of price returns to measure market volatility.
        Type: Analysis
        Parameters:
            - symbol (string): The trading pair symbol (e.g., BTC/USDT).
            - timeframe (string): The timeframe for analysis (e.g., 1h, 1d).
            - limit (integer): Number of historical data points to analyze (default: 50).
            - exchange (string): The exchange to query (default: binance).
        Return Value: A string summarizing the volatility level.
        Invocation: {"tool_name": "get_volatility", "parameters": {"symbol": "BTC/USDT", "timeframe": "1h", "limit": 50, "exchange": "binance"}}
        """
        try:
            exchange_class = getattr(ccxt, exchange.lower(), None)
            if not exchange_class:
                return f"Unsupported exchange: {exchange}. Supported exchanges include 'binance', 'coinbase', etc."
            exchange_instance = exchange_class({'enableRateLimit': True})
            ohlcv = await exchange_instance.fetch_ohlcv(symbol, timeframe, limit=limit)
            if not ohlcv or len(ohlcv) < 2:
                return f"Insufficient historical data for {symbol} on {exchange} to calculate volatility."
            closes = np.array([candle[4] for candle in ohlcv])
            returns = np.diff(closes) / closes[:-1]
            volatility = np.std(returns) * np.sqrt(24 * 365) if timeframe == "1h" else np.std(returns) * np.sqrt(365) if timeframe == "1d" else np.std(returns)
            level = "High" if volatility > 0.5 else "Moderate" if volatility > 0.2 else "Low"
            await exchange_instance.close()
            return f"Volatility for {symbol} on {exchange} (timeframe: {timeframe}, annualized): {volatility:.2%} ({level})"
        except Exception as e:
            logger.error(f"Error calculating volatility for {symbol} on {exchange}: {str(e)}")
            return f"Failed to calculate volatility for {symbol} on {exchange}: {str(e)}"


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
    "get_support_resistance": MarketTools.get_support_resistance,
    "get_top_movers": MarketTools.get_top_movers,
    "get_funding_rate": MarketTools.get_funding_rate,
    "get_volatility": MarketTools.get_volatility,
}
