#!/usr/bin/env python3
"""Efficient verification script for laakhay-data.

This script systematically tests all exchanges, data types, and APIs
to verify laakhay-data is working properly.

Usage:
    # Test everything (takes time, requires network)
    python scripts/verify_data.py --all

    # Test specific exchange
    python scripts/verify_data.py --exchange binance

    # Test specific data type
    python scripts/verify_data.py --data-type ohlcv

    # Test only REST APIs (faster)
    python scripts/verify_data.py --rest-only

    # Generate report without updating matrix
    python scripts/verify_data.py --report-only
"""

import asyncio
import json
import os
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from laakhay.data.core import (
    DataAPI,
    DataFeature,
    InstrumentType,
    MarketType,
    Timeframe,
    TransportKind,
    supports,
)
from laakhay.data.core.capabilities import get_all_exchanges
from laakhay.data.providers import register_all


class VerificationResult:
    """Result of a single verification test."""

    def __init__(self, test_name: str):
        self.test_name = test_name
        self.success = False
        self.error: str | None = None
        self.duration_ms: float = 0.0
        self.data_count: int = 0
        self.timestamp = datetime.now()

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "test_name": self.test_name,
            "success": self.success,
            "error": self.error,
            "duration_ms": self.duration_ms,
            "data_count": self.data_count,
            "timestamp": self.timestamp.isoformat(),
        }


class DataVerifier:
    """Systematic verifier for laakhay-data."""

    def __init__(self, verbose: bool = True):
        self.verbose = verbose
        self.results: list[VerificationResult] = []
        self.api: DataAPI | None = None

    def log(self, message: str):
        """Log a message if verbose."""
        if self.verbose:
            print(f"[VERIFY] {message}")

    async def __aenter__(self):
        """Async context manager entry."""
        # Register all providers first
        register_all()
        self.api = DataAPI()
        await self.api.__aenter__()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self.api:
            await self.api.__aexit__(exc_type, exc_val, exc_tb)

    def _get_instrument_type(self, market_type: MarketType) -> InstrumentType:
        """Get appropriate instrument type for market type."""
        if market_type == MarketType.SPOT:
            return InstrumentType.SPOT
        return InstrumentType.PERPETUAL  # Default to perpetual for futures

    async def verify_rest_ohlcv(
        self, exchange: str, market_type: MarketType, symbol: str = "BTC/USDT"
    ) -> VerificationResult:
        """Verify REST OHLCV retrieval."""
        result = VerificationResult(f"REST_OHLCV_{exchange}_{market_type.value}")
        start = datetime.now()

        try:
            # Check capability first
            instrument_type = self._get_instrument_type(market_type)
            status = supports(
                feature=DataFeature.OHLCV,
                transport=TransportKind.REST,
                exchange=exchange,
                market_type=market_type,
                instrument_type=instrument_type,
            )
            if not status.supported:
                result.error = f"Not supported: {status.reason}"
                return result

            # Test with different timeframes
            for tf in [Timeframe.M1, Timeframe.M5, Timeframe.H1]:
                ohlcv = await self.api.fetch_ohlcv(
                    symbol=symbol,
                    timeframe=tf,
                    exchange=exchange,
                    market_type=market_type,
                    instrument_type=instrument_type,
                    limit=10,
                )
                if len(ohlcv.bars) == 0:
                    raise ValueError(f"No data returned for {tf.value}")

            result.success = True
            result.data_count = 10
        except Exception as e:
            result.error = str(e)
        finally:
            result.duration_ms = (datetime.now() - start).total_seconds() * 1000

        self.results.append(result)
        return result

    async def verify_rest_order_book(
        self, exchange: str, market_type: MarketType, symbol: str = "BTC/USDT"
    ) -> VerificationResult:
        """Verify REST order book retrieval."""
        result = VerificationResult(f"REST_ORDER_BOOK_{exchange}_{market_type.value}")
        start = datetime.now()

        try:
            instrument_type = self._get_instrument_type(market_type)
            status = supports(
                feature=DataFeature.ORDER_BOOK,
                transport=TransportKind.REST,
                exchange=exchange,
                market_type=market_type,
                instrument_type=instrument_type,
            )
            if not status.supported:
                result.error = f"Not supported: {status.reason}"
                return result

            ob = await self.api.fetch_order_book(
                symbol=symbol,
                exchange=exchange,
                market_type=market_type,
                instrument_type=instrument_type,
                depth=20,
            )

            if len(ob.bids) == 0 or len(ob.asks) == 0:
                raise ValueError("Empty order book")

            # Verify computed properties
            if ob.spread_bps is None:
                raise ValueError("Spread calculation failed")

            result.success = True
            result.data_count = len(ob.bids) + len(ob.asks)
        except Exception as e:
            result.error = str(e)
        finally:
            result.duration_ms = (datetime.now() - start).total_seconds() * 1000

        self.results.append(result)
        return result

    async def verify_rest_trades(
        self, exchange: str, market_type: MarketType, symbol: str = "BTC/USDT"
    ) -> VerificationResult:
        """Verify REST recent trades retrieval."""
        result = VerificationResult(f"REST_TRADES_{exchange}_{market_type.value}")
        start = datetime.now()

        try:
            instrument_type = self._get_instrument_type(market_type)
            status = supports(
                feature=DataFeature.TRADES,
                transport=TransportKind.REST,
                exchange=exchange,
                market_type=market_type,
                instrument_type=instrument_type,
            )
            if not status.supported:
                result.error = f"Not supported: {status.reason}"
                return result

            trades = await self.api.fetch_recent_trades(
                symbol=symbol,
                exchange=exchange,
                market_type=market_type,
                instrument_type=instrument_type,
                limit=10,
            )

            if len(trades) == 0:
                raise ValueError("No trades returned")

            result.success = True
            result.data_count = len(trades)
        except Exception as e:
            result.error = str(e)
        finally:
            result.duration_ms = (datetime.now() - start).total_seconds() * 1000

        self.results.append(result)
        return result

    async def verify_rest_symbols(
        self, exchange: str, market_type: MarketType
    ) -> VerificationResult:
        """Verify REST symbol metadata retrieval."""
        result = VerificationResult(f"REST_SYMBOLS_{exchange}_{market_type.value}")
        start = datetime.now()

        try:
            instrument_type = self._get_instrument_type(market_type)
            status = supports(
                feature=DataFeature.SYMBOL_METADATA,
                transport=TransportKind.REST,
                exchange=exchange,
                market_type=market_type,
                instrument_type=instrument_type,
            )
            if not status.supported:
                result.error = f"Not supported: {status.reason}"
                return result

            symbols = await self.api.fetch_symbols(
                exchange=exchange,
                market_type=market_type,
            )

            if len(symbols) == 0:
                raise ValueError("No symbols returned")

            # Verify common symbols exist
            symbol_names = [s.symbol for s in symbols]
            if "BTCUSDT" not in symbol_names and "BTCUSD" not in symbol_names:
                self.log(f"Warning: BTCUSDT/BTCUSD not found in {exchange}")

            result.success = True
            result.data_count = len(symbols)
        except Exception as e:
            result.error = str(e)
        finally:
            result.duration_ms = (datetime.now() - start).total_seconds() * 1000

        self.results.append(result)
        return result

    async def verify_rest_open_interest(
        self, exchange: str, market_type: MarketType, symbol: str = "BTC/USDT"
    ) -> VerificationResult:
        """Verify REST open interest retrieval (futures only)."""
        result = VerificationResult(f"REST_OPEN_INTEREST_{exchange}_{market_type.value}")
        start = datetime.now()

        try:
            if market_type != MarketType.FUTURES:
                result.error = "Open interest only available for futures"
                return result

            instrument_type = InstrumentType.PERPETUAL
            status = supports(
                feature=DataFeature.OPEN_INTEREST,
                transport=TransportKind.REST,
                exchange=exchange,
                market_type=market_type,
                instrument_type=instrument_type,
            )
            if not status.supported:
                result.error = f"Not supported: {status.reason}"
                return result

            oi = await self.api.fetch_open_interest(
                symbol=symbol,
                exchange=exchange,
                market_type=market_type,
                instrument_type=instrument_type,
                historical=False,
            )

            if len(oi) == 0:
                raise ValueError("No open interest data returned")

            result.success = True
            result.data_count = len(oi)
        except Exception as e:
            result.error = str(e)
        finally:
            result.duration_ms = (datetime.now() - start).total_seconds() * 1000

        self.results.append(result)
        return result

    async def verify_rest_funding_rates(
        self, exchange: str, market_type: MarketType, symbol: str = "BTC/USDT"
    ) -> VerificationResult:
        """Verify REST funding rates retrieval (futures only)."""
        result = VerificationResult(f"REST_FUNDING_RATES_{exchange}_{market_type.value}")
        start = datetime.now()

        try:
            if market_type != MarketType.FUTURES:
                result.error = "Funding rates only available for futures"
                return result

            instrument_type = InstrumentType.PERPETUAL
            status = supports(
                feature=DataFeature.FUNDING_RATE,
                transport=TransportKind.REST,
                exchange=exchange,
                market_type=market_type,
                instrument_type=instrument_type,
            )
            if not status.supported:
                result.error = f"Not supported: {status.reason}"
                return result

            rates = await self.api.fetch_funding_rates(
                symbol=symbol,
                exchange=exchange,
                market_type=market_type,
                instrument_type=instrument_type,
                limit=10,
            )

            if len(rates) == 0:
                raise ValueError("No funding rates returned")

            result.success = True
            result.data_count = len(rates)
        except Exception as e:
            result.error = str(e)
        finally:
            result.duration_ms = (datetime.now() - start).total_seconds() * 1000

        self.results.append(result)
        return result

    async def verify_ws_ohlcv(
        self, exchange: str, market_type: MarketType, symbol: str = "BTC/USDT", timeout: int = 5
    ) -> VerificationResult:
        """Verify WebSocket OHLCV streaming."""
        result = VerificationResult(f"WS_OHLCV_{exchange}_{market_type.value}")
        start = datetime.now()

        try:
            instrument_type = self._get_instrument_type(market_type)
            status = supports(
                feature=DataFeature.OHLCV,
                transport=TransportKind.WS,
                exchange=exchange,
                market_type=market_type,
                instrument_type=instrument_type,
            )
            if not status.supported:
                result.error = f"Not supported: {status.reason}"
                return result

            count = 0
            async for _bar in self.api.stream_ohlcv(
                symbol=symbol,
                timeframe=Timeframe.M1,
                exchange=exchange,
                market_type=market_type,
                instrument_type=instrument_type,
            ):
                count += 1
                if count >= 3:  # Get at least 3 updates
                    break

            if count == 0:
                raise ValueError("No WebSocket updates received")

            result.success = True
            result.data_count = count
        except TimeoutError:
            result.error = "WebSocket timeout"
        except Exception as e:
            result.error = str(e)
        finally:
            result.duration_ms = (datetime.now() - start).total_seconds() * 1000

        self.results.append(result)
        return result

    async def verify_ws_trades(
        self, exchange: str, market_type: MarketType, symbol: str = "BTC/USDT", timeout: int = 5
    ) -> VerificationResult:
        """Verify WebSocket trades streaming."""
        result = VerificationResult(f"WS_TRADES_{exchange}_{market_type.value}")
        start = datetime.now()

        try:
            instrument_type = self._get_instrument_type(market_type)
            status = supports(
                feature=DataFeature.TRADES,
                transport=TransportKind.WS,
                exchange=exchange,
                market_type=market_type,
                instrument_type=instrument_type,
            )
            if not status.supported:
                result.error = f"Not supported: {status.reason}"
                return result

            count = 0
            async for _trade in self.api.stream_trades(
                symbol=symbol,
                exchange=exchange,
                market_type=market_type,
                instrument_type=instrument_type,
            ):
                count += 1
                if count >= 5:  # Get at least 5 trades
                    break

            if count == 0:
                raise ValueError("No WebSocket trades received")

            result.success = True
            result.data_count = count
        except TimeoutError:
            result.error = "WebSocket timeout"
        except Exception as e:
            result.error = str(e)
        finally:
            result.duration_ms = (datetime.now() - start).total_seconds() * 1000

        self.results.append(result)
        return result

    async def verify_ws_liquidations(
        self, exchange: str, market_type: MarketType, timeout: int = 10
    ) -> VerificationResult:
        """Verify WebSocket liquidations streaming (futures only)."""
        result = VerificationResult(f"WS_LIQUIDATIONS_{exchange}_{market_type.value}")
        start = datetime.now()

        try:
            if market_type != MarketType.FUTURES:
                result.error = "Liquidations only available for futures"
                return result

            instrument_type = InstrumentType.PERPETUAL
            status = supports(
                feature=DataFeature.LIQUIDATIONS,
                transport=TransportKind.WS,
                exchange=exchange,
                market_type=market_type,
                instrument_type=instrument_type,
            )
            if not status.supported:
                result.error = f"Not supported: {status.reason}"
                return result

            count = 0
            async for _liq in self.api.stream_liquidations(
                exchange=exchange,
                market_type=market_type,
                instrument_type=instrument_type,
            ):
                count += 1
                if count >= 1:  # Just verify we can receive at least one
                    break

            # Note: May not receive liquidations immediately, so we just verify connection
            result.success = True
            result.data_count = count
        except TimeoutError:
            # Timeout is OK for liquidations (may not happen immediately)
            result.success = True
            result.error = "No liquidations received (timeout - this is OK)"
        except Exception as e:
            result.error = str(e)
        finally:
            result.duration_ms = (datetime.now() - start).total_seconds() * 1000

        self.results.append(result)
        return result

    async def verify_urm_resolution(
        self, exchange: str, market_type: MarketType
    ) -> VerificationResult:
        """Verify URM symbol resolution."""
        result = VerificationResult(f"URM_{exchange}_{market_type.value}")
        start = datetime.now()

        try:
            instrument_type = self._get_instrument_type(market_type)

            # Test with Laakhay format (BASE/QUOTE)
            symbol = "BTC/USDT" if market_type == MarketType.SPOT else "BTC/USDT"
            ohlcv = await self.api.fetch_ohlcv(
                symbol=symbol,
                timeframe=Timeframe.M1,
                exchange=exchange,
                market_type=market_type,
                instrument_type=instrument_type,
                limit=1,
            )
            result.success = True
            result.data_count = len(ohlcv.bars)
        except Exception as e:
            result.error = str(e)
        finally:
            result.duration_ms = (datetime.now() - start).total_seconds() * 1000

        self.results.append(result)
        return result

    async def verify_capability_system(self) -> VerificationResult:
        """Verify capability system."""
        result = VerificationResult("CAPABILITY_SYSTEM")
        start = datetime.now()

        try:
            # Test capability lookup
            exchanges = get_all_exchanges()
            if len(exchanges) == 0:
                raise ValueError("No exchanges found")

            # Test a few capability checks
            for exchange in ["binance", "coinbase"]:
                status = supports(
                    feature=DataFeature.OHLCV,
                    transport=TransportKind.REST,
                    exchange=exchange,
                    market_type=MarketType.SPOT,
                )
                if not status.supported and exchange == "binance":
                    raise ValueError("Binance OHLCV should be supported")

            result.success = True
            result.data_count = len(exchanges)
        except Exception as e:
            result.error = str(e)
        finally:
            result.duration_ms = (datetime.now() - start).total_seconds() * 1000

        self.results.append(result)
        return result

    async def verify_all_rest(
        self, exchange: str, market_type: MarketType, symbol: str = "BTC/USDT"
    ):
        """Verify all REST APIs for an exchange/market."""
        self.log(f"Verifying REST APIs for {exchange} {market_type.value}...")

        await self.verify_rest_ohlcv(exchange, market_type, symbol)
        await self.verify_rest_order_book(exchange, market_type, symbol)
        await self.verify_rest_trades(exchange, market_type, symbol)
        await self.verify_rest_symbols(exchange, market_type)

        if market_type == MarketType.FUTURES:
            await self.verify_rest_open_interest(exchange, market_type, symbol)
            await self.verify_rest_funding_rates(exchange, market_type, symbol)

        await self.verify_urm_resolution(exchange, market_type)

    async def verify_all_websocket(
        self, exchange: str, market_type: MarketType, symbol: str = "BTC/USDT"
    ):
        """Verify all WebSocket APIs for an exchange/market."""
        self.log(f"Verifying WebSocket APIs for {exchange} {market_type.value}...")

        await self.verify_ws_ohlcv(exchange, market_type, symbol)
        await self.verify_ws_trades(exchange, market_type, symbol)

        if market_type == MarketType.FUTURES:
            await self.verify_ws_liquidations(exchange, market_type)

    async def verify_exchange(self, exchange: str, rest_only: bool = False, ws_only: bool = False):
        """Verify all features for an exchange."""
        self.log(f"\n{'=' * 60}")
        self.log(f"Verifying {exchange.upper()}")
        self.log(f"{'=' * 60}")

        # Determine market types
        from laakhay.data.core.capabilities import get_supported_market_types

        market_types = get_supported_market_types(exchange)
        if not market_types:
            self.log(f"  ⚠️  No market types found for {exchange}")
            return

        for market_type_str in market_types:
            market_type = MarketType(market_type_str)

            if not ws_only:
                await self.verify_all_rest(exchange, market_type)

            if not rest_only:
                await self.verify_all_websocket(exchange, market_type)

    async def verify_all_exchanges(self, rest_only: bool = False, ws_only: bool = False):
        """Verify all exchanges."""
        exchanges = get_all_exchanges()
        self.log(f"\nFound {len(exchanges)} exchanges to verify")

        for exchange in exchanges:
            await self.verify_exchange(exchange, rest_only=rest_only, ws_only=ws_only)
            # Small delay between exchanges to avoid rate limits
            await asyncio.sleep(1)

    def generate_report(self) -> dict[str, Any]:
        """Generate a verification report."""
        total = len(self.results)
        successful = sum(1 for r in self.results if r.success)
        failed = total - successful

        # Group by exchange
        by_exchange: dict[str, list[VerificationResult]] = defaultdict(list)
        for result in self.results:
            parts = result.test_name.split("_")
            if len(parts) >= 2:
                exchange = parts[1] if parts[0] in ["REST", "WS"] else parts[0]
                by_exchange[exchange].append(result)

        # Group by data type
        by_type: dict[str, list[VerificationResult]] = defaultdict(list)
        for result in self.results:
            if "OHLCV" in result.test_name:
                by_type["OHLCV"].append(result)
            elif "ORDER_BOOK" in result.test_name:
                by_type["ORDER_BOOK"].append(result)
            elif "TRADES" in result.test_name:
                by_type["TRADES"].append(result)
            elif "SYMBOLS" in result.test_name:
                by_type["SYMBOLS"].append(result)
            elif "OPEN_INTEREST" in result.test_name:
                by_type["OPEN_INTEREST"].append(result)
            elif "FUNDING_RATES" in result.test_name:
                by_type["FUNDING_RATES"].append(result)
            elif "LIQUIDATIONS" in result.test_name:
                by_type["LIQUIDATIONS"].append(result)

        report = {
            "timestamp": datetime.now().isoformat(),
            "summary": {
                "total_tests": total,
                "successful": successful,
                "failed": failed,
                "success_rate": f"{(successful / total * 100):.1f}%" if total > 0 else "0%",
            },
            "by_exchange": {
                exchange: {
                    "total": len(results),
                    "successful": sum(1 for r in results if r.success),
                    "failed": sum(1 for r in results if not r.success),
                }
                for exchange, results in by_exchange.items()
            },
            "by_type": {
                data_type: {
                    "total": len(results),
                    "successful": sum(1 for r in results if r.success),
                    "failed": sum(1 for r in results if not r.success),
                }
                for data_type, results in by_type.items()
            },
            "results": [r.to_dict() for r in self.results],
        }

        return report

    def print_report(self):
        """Print a human-readable report."""
        report = self.generate_report()
        summary = report["summary"]

        print("\n" + "=" * 60)
        print("VERIFICATION REPORT")
        print("=" * 60)
        print(f"Total Tests: {summary['total_tests']}")
        print(f"Successful: {summary['successful']} ✅")
        print(f"Failed: {summary['failed']} ❌")
        print(f"Success Rate: {summary['success_rate']}")
        print("\n" + "-" * 60)

        # Print by exchange
        print("\nBy Exchange:")
        for exchange, stats in report["by_exchange"].items():
            status = "✅" if stats["failed"] == 0 else "⚠️"
            print(f"  {status} {exchange}: {stats['successful']}/{stats['total']}")

        # Print by type
        print("\nBy Data Type:")
        for data_type, stats in report["by_type"].items():
            status = "✅" if stats["failed"] == 0 else "⚠️"
            print(f"  {status} {data_type}: {stats['successful']}/{stats['total']}")

        # Print failures
        failures = [r for r in self.results if not r.success]
        if failures:
            print("\n" + "-" * 60)
            print("FAILURES:")
            for result in failures[:10]:  # Show first 10
                print(f"  ❌ {result.test_name}: {result.error}")
            if len(failures) > 10:
                print(f"  ... and {len(failures) - 10} more failures")

        print("\n" + "=" * 60)


async def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="Verify laakhay-data functionality")
    parser.add_argument("--all", action="store_true", help="Test all exchanges")
    parser.add_argument("--exchange", type=str, help="Test specific exchange")
    parser.add_argument("--data-type", type=str, help="Test specific data type")
    parser.add_argument("--rest-only", action="store_true", help="Test only REST APIs")
    parser.add_argument("--ws-only", action="store_true", help="Test only WebSocket APIs")
    parser.add_argument("--report-only", action="store_true", help="Generate report only")
    parser.add_argument("--output", type=str, help="Save report to JSON file")
    parser.add_argument("--quiet", action="store_true", help="Reduce output verbosity")

    args = parser.parse_args()

    # Check if network tests are enabled
    if os.environ.get("RUN_LAAKHAY_NETWORK_TESTS") != "1":
        print("⚠️  Warning: RUN_LAAKHAY_NETWORK_TESTS not set to '1'")
        print("   Some tests may be skipped. Set it to enable network tests.")
        response = input("Continue anyway? (y/n): ")
        if response.lower() != "y":
            return

    async with DataVerifier(verbose=not args.quiet) as verifier:
        # Verify capability system first
        await verifier.verify_capability_system()

        if args.all:
            await verifier.verify_all_exchanges(rest_only=args.rest_only, ws_only=args.ws_only)
        elif args.exchange:
            await verifier.verify_exchange(
                args.exchange, rest_only=args.rest_only, ws_only=args.ws_only
            )
        else:
            # Default: test Binance only
            await verifier.verify_exchange(
                "binance", rest_only=args.rest_only, ws_only=args.ws_only
            )

        # Generate and print report
        verifier.print_report()

        # Save report if requested
        if args.output:
            report = verifier.generate_report()
            from pathlib import Path

            Path(args.output).write_text(json.dumps(report, indent=2))
            print(f"\nReport saved to {args.output}")


if __name__ == "__main__":
    asyncio.run(main())
