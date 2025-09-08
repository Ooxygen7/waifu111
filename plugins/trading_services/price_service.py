"""
价格服务
负责获取和缓存实时期货价格信息
"""

import asyncio
import ccxt
import logging
from datetime import datetime, timedelta
from typing import Dict, Optional

from bot_core.data_repository.trading_repository import TradingRepository
from utils.logging_utils import setup_logging

setup_logging()
logger = logging.getLogger(__name__)

# 屏蔽ccxt的日志输出
logging.getLogger('ccxt').setLevel(logging.WARNING)
logging.getLogger('ccxt.base').setLevel(logging.WARNING)
logging.getLogger('ccxt.bybit').setLevel(logging.WARNING)


class PriceService:
    """
    价格服务类
    管理实时期货价格数据的获取和缓存
    """

    def __init__(self):
        # 初始化交易所连接(使用Bybit作为价格源)
        self.exchange = ccxt.bybit({
            'sandbox': False,  # 使用实盘数据但不实际交易
            'enableRateLimit': True,
        })

        # 价格缓存相关
        self.price_cache = {}  # 本地价格缓存 {symbol: price}
        self.last_update = {}  # 最后更新时间 {symbol: datetime}
        self.cache_expiry = 10  # 缓存过期时间(秒)

        logger.info("价格服务已初始化")

    async def get_current_price(self, symbol: str) -> Optional[float]:
        """
        获取实时价格，支持缓存机制

        Args:
            symbol: 交易对，如'BTC/USDT'

        Returns:
            当前价格，如果获取失败返回None
        """
        try:
            # 标准化交易对格式
            if '/' not in symbol:
                symbol = f"{symbol.upper()}/USDT"

            # 检查缓存是否有效
            now = datetime.now()
            if (symbol in self.price_cache and
                symbol in self.last_update and
                (now - self.last_update[symbol]).seconds < self.cache_expiry):
                return self.price_cache[symbol]

            # 从交易所获取最新价格
            ticker = await asyncio.get_event_loop().run_in_executor(
                None, self.exchange.fetch_ticker, symbol
            )

            price_val = ticker.get('last')
            if price_val is None:
                logger.warning(f"获取的ticker中'last'价格为空: {symbol}")
                return self._get_cached_price(symbol)

            price = float(price_val)

            # 更新本地缓存
            self.price_cache[symbol] = price
            self.last_update[symbol] = now

            # 异步更新数据库缓存(不阻塞)
            asyncio.create_task(self._update_db_cache(symbol, price))

            logger.debug(f"获取价格成功 {symbol}: {price}")
            return price

        except Exception as e:
            logger.error(f"获取价格失败 {symbol}: {e}")
            # 从数据库获取历史价格
            return self._get_cached_price(symbol)

    async def get_real_time_price(self, symbol: str) -> Optional[float]:
        """
        强制获取实时价格，绕过缓存机制
        专门用于市价开单和平仓操作，确保价格的实时性

        Args:
            symbol: 交易对，如'BTC/USDT'

        Returns:
            当前价格，如果获取失败返回None
        """
        try:
            # 标准化交易对格式
            if '/' not in symbol:
                symbol = f"{symbol.upper()}/USDT"

            logger.debug(f"强制获取实时价格: {symbol}")

            # 直接从交易所获取最新价格，不使用缓存
            ticker = await asyncio.get_event_loop().run_in_executor(
                None, self.exchange.fetch_ticker, symbol
            )

            price_val = ticker.get('last')
            if price_val is None:
                logger.warning(f"获取的ticker中'last'价格为空: {symbol}")
                # 如果交易所返回空价格，尝试从缓存获取
                return self._get_cached_price(symbol)

            price = float(price_val)

            # 更新本地缓存
            now = datetime.now()
            self.price_cache[symbol] = price
            self.last_update[symbol] = now

            # 异步更新数据库缓存(不阻塞)
            asyncio.create_task(self._update_db_cache(symbol, price))

            logger.debug(f"获取实时价格成功 {symbol}: {price}")
            return price

        except Exception as e:
            logger.error(f"强制获取实时价格失败 {symbol}: {e}")
            # 如果实时获取失败，降级到缓存价格
            logger.warning(f"降级使用缓存价格: {symbol}")
            return self._get_cached_price(symbol)

    def _get_cached_price(self, symbol: str) -> Optional[float]:
        """从数据库获取缓存价格"""
        try:
            result = TradingRepository.get_price_cache(symbol)
            if result["success"] and result["cache"]:
                price = result["cache"]["price"]
                logger.debug(f"使用缓存价格 {symbol}: {price}")
                return price
            logger.warning(f"价格缓存不存在: {symbol}")
            return None
        except Exception as e:
            logger.error(f"从数据库获取价格缓存失败 {symbol}: {e}")
            return None

    async def _update_db_cache(self, symbol: str, price: float):
        """异步更新数据库价格缓存"""
        try:
            result = TradingRepository.update_price_cache(symbol, price)
            if not result["success"]:
                logger.error(f"更新价格缓存失败: {result.get('error')}")
        except Exception as e:
            logger.error(f"异步更新价格缓存失败 {symbol}: {e}")

    async def get_multiple_prices(self, symbols: list) -> Dict[str, Optional[float]]:
        """
        批量获取多个交易对的价格

        Args:
            symbols: 交易对列表

        Returns:
            {symbol: price} 字典
        """
        tasks = []
        for symbol in symbols:
            tasks.append(self.get_current_price(symbol))

        results = await asyncio.gather(*tasks, return_exceptions=True)

        prices = {}
        for i, result in enumerate(results):
            symbol = symbols[i]
            if isinstance(result, Exception):
                logger.error(f"批量获取价格失败 {symbol}: {result}")
                prices[symbol] = None
            else:
                prices[symbol] = result

        return prices

    def clear_cache(self):
        """清除所有缓存"""
        self.price_cache.clear()
        self.last_update.clear()
        logger.info("价格缓存已清除")

    def clear_cache_for_symbol(self, symbol: str):
        """清除指定交易对的缓存"""
        symbol_with_usdt = f"{symbol}/USDT" if '/' not in symbol else symbol
        self.price_cache.pop(symbol_with_usdt, None)
        self.last_update.pop(symbol_with_usdt, None)
        logger.debug(f"清除价格缓存: {symbol_with_usdt}")

    def get_cache_status(self) -> Dict:
        """获取缓存状态信息"""
        return {
            "cached_symbols": list(self.price_cache.keys()),
            "cache_count": len(self.price_cache),
            "cache_expiry_seconds": self.cache_expiry
        }


# 全局价格服务实例
price_service = PriceService()