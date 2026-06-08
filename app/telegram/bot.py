from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, BotCommand
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
)
import os
import asyncio
from datetime import datetime

from app.config import Config
from app.services.stock_service import (
    get_latest_data,
    get_top_gainers,
    get_top_losers,
    get_top_volume,
    STOCK_LIST,
)
from app.services.analysis_service import AnalysisService
from app.services.market_service import get_market_summary, get_market_sentiment, get_sector_performance
from app.charts.chart_generator import generate_full_analysis_chart
from app.database import crud
from app.database import ai_crud
from app.ai.learning_engine import LearningEngine
from app.ai.strategies.bpjs_strategy import BPJSStrategy
from app.ai.strategies.creative_trader_strategy import CreativeTraderStrategy
from app.services.broker_service import save_and_analyze_broker_data, format_broker_help


class TelegramBot:
    """Telegram bot for AI Stock Analyzer Indonesia."""

    def __init__(self):
        self.token = Config.TELEGRAM_BOT_TOKEN
        self.app = None
        self.analysis_service = AnalysisService()
        self.learning = LearningEngine()

    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /start command - welcome message."""
        try:
            user = update.effective_user
            db_user = crud.add_user(telegram_id=user.id, username=user.username)

            await update.message.reply_text(
                f"🤖 *AI Stock Analyzer Indonesia*\n\n"
                f"Halo {user.first_name}! Saya adalah bot analisa saham IDX.\n\n"
                f"*Commands:*\n"
                f"/analyze BBCA - Analisa saham\n"
                f"/watchlist - Lihat watchlist\n"
                f"/add BBCA - Tambah ke watchlist\n"
                f"/remove BBCA - Hapus dari watchlist\n"
                f"/topgainer - Top gainer hari ini\n"
                f"/toploser - Top loser hari ini\n"
                f"/topvolume - Top volume\n"
                f"/market - Ringkasan market\n"
                f"/sentiment - Sentimen market\n"
                f"/rekomendasi - Rekomendasi beli besok\n"
                f"/daytrade BBCA - BPJS Day Trade signal\n"
                f"/bpjs - Kandidat BPJS hari ini\n"
                f"/longterm BBCA - Long term akumulasi\n"
                f"/longtermcandidates - Kandidat long term\n"
                f"/broker BBCA - Input data broker asing\n"
                f"/brokerhelp - Panduan input broker\n"
                f"/feedback benar BBCA - Beri feedback\n"
                f"/accuracy - Skor AI\n"
                f"/performance - Performa AI\n"
                f"/strategy - Mode strategi\n"
                f"/help - Bantuan\n\n"
                f"Contoh: /analyze BBCA",
                parse_mode="Markdown",
            )
        except Exception as e:
            print(f"Error in start: {e}")
            await update.message.reply_text(
                "❌ Error: /start tidak tersedia saat ini"
            )

    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /help command - list all commands."""
        try:
            help_text = (
                "📚 *Bantuan AI Stock Analyzer*\n\n"
                "*Analisa Saham:*\n"
                "/analyze BBCA - Analisa detail + chart\n"
                "/rekomendasi - Rekomendasi saham beli besok\n\n"
                "*Watchlist:*\n"
                "/add BBCA - Tambah saham\n"
                "/remove BBCA - Hapus saham\n"
                "/watchlist - Daftar watchlist\n\n"
                "*Foreign Flow:*\n"
                "/marketreport - Laporan asing vs lokal (hidden)\n"
                "/market - Overview market IDX (termasuk data asing)\n"
                "🔍 Cari saham dengan net foreign > 0 (asing akumulasi)\n\n"
                "*Market:*\n"
                "/topgainer - Top gainer hari ini\n"
                "/toploser - Top loser hari ini\n"
                "/topvolume - Top volume perdagangan\n"
                "/market - Overview market IDX\n"
                "/sentiment - Sentimen market\n\n"
                "*Dashboard:*\n"
                "/overview - Overview market IDX\n"
                "/movers - Top gainers/losers/volume\n"
                "/sectors - Performa sektor\n"
                "/predictions - Prediksi & alert terbaru\n\n"
                "*Strategi:*\n"
                "/daytrade BBCA - BPJS Day Trade signal\n"
                "/bpjs - Kandidat BPJS hari ini\n"
                "/longterm BBCA - Long term akumulasi\n"
                "/longtermcandidates - Kandidat long term\n\n"
                "*Broker Tracking:*\n"
                "/broker BBCA - Input data broker asing/domestik\n"
                "/brokerhelp - Panduan format input broker\n\n"
                "*AI & Feedback:*\n"
                "/feedback benar BBCA - Kirim feedback\n"
                "/accuracy - Akurasi prediksi AI\n"
                "/performance - Performa prediksi\n"
                "/strategy - Mode strategi aktif\n\n"
                "*Saham tersedia:*\n"
                f"{', '.join(sorted(STOCK_LIST.keys())[:10])}\n"
                "dan lainnya..."
            )
            await update.message.reply_text(help_text, parse_mode="Markdown")
        except Exception as e:
            print(f"Error in help: {e}")
            await update.message.reply_text(
                "❌ Error: /help tidak tersedia saat ini"
            )

    async def analyze(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /analyze command - analyze single stock."""
        try:
            if not context.args:
                await update.message.reply_text("Gunakan: /analyze BBCA")
                return

            code = context.args[0].upper()
            await update.message.reply_text(f"🔍 Menganalisa {code}...")

            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None, lambda: self.analysis_service.analyze_stock(code, use_ai=True)
            )

            if "error" in result:
                await update.message.reply_text(f"❌ {result['error']}")
                return

            chart_path = None
            df = result.get("dataframe")
            if df is not None:
                try:
                    chart_path = generate_full_analysis_chart(
                        df, result["stock_code"], result.get("stock_name", "")
                    )
                except Exception as e:
                    print(f"Chart error: {e}")

            emoji = {"BUY": "🟢", "HOLD": "🟡", "SELL": "🔴"}
            rec_emoji = emoji.get(result["recommendation"], "⚪")

            source = result.get("source", "unknown")
            source_emoji = {"ai_api": "🤖", "cache": "💾", "database": "💾", "rule_based": "⚙️"}
            source_label = {"ai_api": "AI API (live)", "cache": "Cache", "database": "Database", "rule_based": "Rule-based"}
            src_icon = source_emoji.get(source, "❓")
            src_text = source_label.get(source, source)

            message = (
                f"{rec_emoji} *{result['stock_code']}* - {result.get('stock_name', '')}\n"
                f"💰 Harga: Rp{result['price']:,.0f} "
                f"({result['change_pct']:+.2f}%)\n"
                f"📊 *Analisa Teknikal:*\n"
                f"• Trend: {result['trend']}\n"
                f"• RSI: {result['rsi']} ({result['rsi_status']})\n"
                f"• MACD: {result['macd_status']}\n"
                f"• MA20: Rp{result['ma20']:,.0f}\n"
                f"• MA50: Rp{result['ma50']:,.0f}\n"
                f"• Support: Rp{result['support']:,.0f}\n"
                f"• Resistance: Rp{result['resistance']:,.0f}\n\n"
                f"🎯 *Rekomendasi: {result['recommendation']}*\n"
                f"📈 Confidence: {result['confidence']}%\n"
                f"{src_icon} _Sumber: {src_text}_\n\n"
                f"💡 *Reason:*\n{result['reason']}\n\n"
                f"#IDX #{result['stock_code'].replace('.JK', '')}"
            )

            await update.message.reply_text(message, parse_mode="Markdown")

            if chart_path and os.path.exists(chart_path):
                with open(chart_path, "rb") as f:
                    await update.message.reply_photo(
                        photo=f,
                        caption=f"Chart {result['stock_code']} - {result['trend']} | Rec: {result['recommendation']} ({result['confidence']}%)",
                    )
        except Exception as e:
            print(f"Error in analyze: {e}")
            await update.message.reply_text(
                "❌ Error: /analyze tidak tersedia saat ini"
            )

    async def add_watchlist(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /add command - add stock to watchlist."""
        try:
            if not context.args:
                await update.message.reply_text("Gunakan: /add BBCA")
                return

            code = context.args[0].upper()
            user = crud.get_user(update.effective_user.id)
            if not user:
                user = crud.add_user(update.effective_user.id, update.effective_user.username)

            crud.add_to_watchlist(user["id"], code, STOCK_LIST.get(code, ""))
            await update.message.reply_text(f"✅ {code} ditambahkan ke watchlist!")
        except Exception as e:
            print(f"Error in add_watchlist: {e}")
            await update.message.reply_text(
                f"❌ Gagal menambahkan {context.args[0].upper() if context.args else ''} ke watchlist"
            )

    async def remove_watchlist(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /remove command - remove stock from watchlist."""
        try:
            if not context.args:
                await update.message.reply_text("Gunakan: /remove BBCA")
                return

            code = context.args[0].upper()
            user = crud.get_user(update.effective_user.id)
            if user:
                crud.remove_from_watchlist(user["id"], code)

            await update.message.reply_text(f"🗑 {code} dihapus dari watchlist!")
        except Exception as e:
            print(f"Error in remove_watchlist: {e}")
            await update.message.reply_text(
                f"❌ Gagal menghapus {context.args[0].upper() if context.args else ''} dari watchlist"
            )

    async def watchlist(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /watchlist command - show user watchlist."""
        try:
            user = crud.get_user(update.effective_user.id)
            if not user:
                await update.message.reply_text("Kamu belum punya watchlist. Gunakan /add BBCA")
                return

            items = crud.get_watchlist(user["id"])
            if not items:
                await update.message.reply_text("Watchlist kosong. Gunakan /add BBCA")
                return

            message = "📋 *Watchlist:*\n\n"
            for item in items:
                message += f"• {item['stock_code']}"
                if item["stock_name"]:
                    message += f" - {item['stock_name']}"
                message += "\n"

            message += "\nGunakan /analyze BBCA untuk analisa"
            await update.message.reply_text(message, parse_mode="Markdown")
        except Exception as e:
            print(f"Error in watchlist: {e}")
            await update.message.reply_text(
                "❌ Error: /watchlist tidak tersedia saat ini"
            )

    async def top_gainer(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /topgainer command - top gainers today."""
        try:
            await update.message.reply_text("📈 Mengambil data top gainer...")
            gainers = get_top_gainers(10)

            if not gainers:
                await update.message.reply_text("📈 Tidak ada data top gainer saat ini.")
                return

            message = "📈 *Top Gainer Hari Ini:*\n\n"
            for i, g in enumerate(gainers, 1):
                message += f"{i}. {g['code']} - Rp{g['price']:,.0f} ({g['change_pct']:+.2f}%)\n"

            await update.message.reply_text(message, parse_mode="Markdown")
        except Exception as e:
            print(f"Error in top_gainer: {e}")
            await update.message.reply_text(
                "❌ Error: /topgainer tidak tersedia saat ini"
            )

    async def top_loser(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /toploser command - top losers today."""
        try:
            await update.message.reply_text("📉 Mengambil data top loser...")
            losers = get_top_losers(10)

            if not losers:
                await update.message.reply_text("📉 Tidak ada data top loser saat ini.")
                return

            message = "📉 *Top Loser Hari Ini:*\n\n"
            for i, g in enumerate(losers, 1):
                message += f"{i}. {g['code']} - Rp{g['price']:,.0f} ({g['change_pct']:+.2f}%)\n"

            await update.message.reply_text(message, parse_mode="Markdown")
        except Exception as e:
            print(f"Error in top_loser: {e}")
            await update.message.reply_text(
                "❌ Error: /toploser tidak tersedia saat ini"
            )

    async def top_volume(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /topvolume command - top volume today."""
        try:
            await update.message.reply_text("📊 Mengambil data top volume...")
            volumes = get_top_volume(10)

            if not volumes:
                await update.message.reply_text("📊 Tidak ada data top volume saat ini.")
                return

            message = "📊 *Top Volume Hari Ini:*\n\n"
            for i, g in enumerate(volumes, 1):
                message += f"{i}. {g['code']} - {g['volume']:,} lembar\n"

            await update.message.reply_text(message, parse_mode="Markdown")
        except Exception as e:
            print(f"Error in top_volume: {e}")
            await update.message.reply_text(
                "❌ Error: /topvolume tidak tersedia saat ini"
            )

    async def market(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /market command - market summary."""
        try:
            await update.message.reply_text("📊 Mengambil data market...")
            summary = get_market_summary()

            fg = summary["fear_greed"]
            if fg["index"] >= 60:
                fg_emoji = "🟢"
            elif fg["index"] >= 40:
                fg_emoji = "🟡"
            else:
                fg_emoji = "🔴"

            message = (
                "📊 *Ringkasan Market IDX:*\n\n"
                f"📈 Advancing: {summary['advancing']}\n"
                f"📉 Declining: {summary['declining']}\n"
                f"⏸ Unchanged: {summary['unchanged']}\n"
                f"📊 Total: {summary['total_stocks']} saham\n\n"
                f"{fg_emoji} Fear & Greed: {fg['index']} - {fg['label']}\n\n"
                f"Data: {summary['timestamp'][:19]}"
            )

            await update.message.reply_text(message, parse_mode="Markdown")
        except Exception as e:
            print(f"Error in market: {e}")
            await update.message.reply_text(
                "❌ Error: /market tidak tersedia saat ini"
            )

    async def sentiment(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /sentiment command - market sentiment."""
        try:
            sent = get_market_sentiment()
            fg = sent["fear_greed"]

            if sent["sentiment"] == "Bullish":
                emoji = "🟢"
            elif sent["sentiment"] == "Neutral":
                emoji = "🟡"
            else:
                emoji = "🔴"

            message = (
                f"{emoji} *Market Sentiment: {sent['sentiment']}*\n\n"
                f"{sent['description']}\n\n"
                f"📊 Fear & Greed Index: {fg['index']} - {fg['label']}\n"
                f"📈 Advancing: {sent['advancing']}\n"
                f"📉 Declining: {sent['declining']}\n"
                f"📊 A/D Ratio: {sent['advance_decline_ratio']}"
            )

            await update.message.reply_text(message, parse_mode="Markdown")
        except Exception as e:
            print(f"Error in sentiment: {e}")
            await update.message.reply_text(
                "❌ Error: /sentiment tidak tersedia saat ini"
            )

    async def feedback_cmd(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /feedback command - submit feedback."""
        try:
            if not context.args:
                await update.message.reply_text(
                    "Gunakan: /feedback [benar|salah|bullish|bearish] BBCA\n\n"
                    "Contoh: /feedback benar BBCA"
                )
                return

            value = context.args[0].lower()
            code = context.args[1].upper() if len(context.args) > 1 else None

            if value not in ("benar", "salah", "bullish", "bearish"):
                await update.message.reply_text("Feedback: benar, salah, bullish, atau bearish")
                return

            fb_map = {"benar": "helpful", "salah": "wrong",
                       "bullish": "bullish", "bearish": "bearish"}

            user = crud.get_user(update.effective_user.id)
            if not user:
                user = crud.add_user(update.effective_user.id, update.effective_user.username)

            ai_crud.save_feedback(
                user["id"], code or "GENERAL", None,
                "telegram", fb_map[value], None,
            )

            await update.message.reply_text(f"✅ Feedback '{value}' diterima! Terima kasih!")
        except Exception as e:
            print(f"Error in feedback: {e}")
            await update.message.reply_text(
                "❌ Error: /feedback tidak tersedia saat ini"
            )

    async def accuracy_cmd(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /accuracy command - AI accuracy scores."""
        try:
            perf = self.learning.get_performance_summary()
            scores = perf.get("scores", {})

            acc7 = scores.get("accuracy_7d", {})
            acc30 = scores.get("accuracy_30d", {})
            overall = scores.get("accuracy_overall", {})
            winrate = scores.get("winrate", {})
            avg_profit = scores.get("avg_profit", {})

            message = (
                "📊 *AI Learning Performance*\n\n"
                f"🎯 7d Accuracy: {acc7.get('score_value', 0):.1f}% "
                f"({acc7.get('correct_predictions', 0)}/{acc7.get('total_predictions', 0)})\n"
                f"📈 30d Accuracy: {acc30.get('score_value', 0):.1f}%\n"
                f"📊 Overall: {overall.get('score_value', 0):.1f}%\n"
                f"🏆 Winrate: {winrate.get('score_value', 0):.1f}%\n"
                f"💰 Avg Profit: {avg_profit.get('score_value', 0):.2f}%\n\n"
                f"💬 Feedback: "
                f"👍{perf.get('feedback', {}).get('helpful', 0)} "
                f"👎{perf.get('feedback', {}).get('wrong', 0)}"
            )

            await update.message.reply_text(message, parse_mode="Markdown")
        except Exception as e:
            print(f"Error in accuracy: {e}")
            await update.message.reply_text(
                "❌ Error: /accuracy tidak tersedia saat ini"
            )

    async def performance_cmd(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /performance command - AI performance summary."""
        try:
            perf = self.learning.get_performance_summary()
            recent = perf.get("recent_predictions", [])

            message = "📈 *AI Performance Summary*\n\n"
            if recent:
                message += "*Prediksi Terbaru:*\n"
                for p in recent[:5]:
                    emoji = {"SUCCESS": "✅", "FAIL": "❌", "Pending": "⏳"}
                    profit = p.get("profit", 0)
                    profit_str = f" ({profit:+.2f}%)" if profit else ""
                    message += (
                        f"{emoji.get(p.get('actual', 'Pending'), '⏳')} "
                        f"{p['stock']}: {p['prediction']} "
                        f"(Conf: {p.get('confidence', 0)}%)"
                        f"{profit_str}\n"
                    )
            else:
                message += "Belum ada prediksi.\n"

            message += f"\nGunakan /accuracy untuk detail skor."

            await update.message.reply_text(message, parse_mode="Markdown")
        except Exception as e:
            print(f"Error in performance: {e}")
            await update.message.reply_text(
                "❌ Error: /performance tidak tersedia saat ini"
            )

    async def strategy_cmd(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /strategy command - list active strategies."""
        try:
            strategies = ai_crud.get_strategies(active_only=True)
            if not strategies:
                await update.message.reply_text("Belum ada strategi dikonfigurasi.")
                return

            message = "🎯 *Strategy Modes:*\n\n"
            for s in strategies:
                message += (
                    f"• {s.get('display_name', s.get('strategy_name', s['name']))}\n"
                    f"  {s.get('description', '')}\n"
                    f"  Risk: {s.get('risk_profile', '-')} | "
                    f"Period: {s.get('holding_period', '-')}\n\n"
                )

            await update.message.reply_text(message, parse_mode="Markdown")
        except Exception as e:
            print(f"Error in strategy: {e}")
            await update.message.reply_text(
                "❌ Error: /strategy tidak tersedia saat ini"
            )

    async def rekomendasi_cmd(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /rekomendasi command - AI stock recommendations."""
        try:
            await update.message.reply_text("🔍 Mencari rekomendasi saham untuk besok...")

            loop = asyncio.get_event_loop()
            buy_list = await loop.run_in_executor(None, self._scan_buy_list)

            if not buy_list:
                await update.message.reply_text(
                    "📭 *Tidak ada rekomendasi BUY untuk besok.*\n\n"
                    "Semua saham dalam HOLD/SELL.",
                    parse_mode="Markdown"
                )
                return

            buy_list.sort(key=lambda x: x["confidence"], reverse=True)
            top = buy_list[:10]

            msg = (
                "🟢 *REKOMENDASI SAHAM BESOK* 🟢\n"
                f"📅 {datetime.now().strftime('%d %B %Y')}\n"
                f"🎯 Strategi: Day Trading (Pagi Beli, Sore Jual)\n\n"
            )

            for i, s in enumerate(top, 1):
                src_icon = {"ai_api": "🤖", "cache": "💾", "database": "💾"}.get(s["source"], "⚙️")
                msg += (
                    f"{'🟢' if i <= 3 else '🟡'} *{i}. {s['code']}* - {s['name']}\n"
                    f"   💰 Rp{s['price']:,.0f} ({s['change_pct']:+.2f}%)\n"
                    f"   📊 RSI: {s['rsi']} ({s['rsi_status']}) | Trend: {s['trend']}\n"
                    f"   🎯 Confidence: {s['confidence']}% {src_icon}\n"
                    f"   💡 {s['reason'][:100]}\n\n"
                )

            msg += (
                f"\n⚠️ _Data dari {len(buy_list)} saham BUY. "
                f"AI: 9Router. Selalu DYOR!_"
            )

            await update.message.reply_text(msg, parse_mode="Markdown")
        except Exception as e:
            print(f"Error in rekomendasi: {e}")
            await update.message.reply_text(
                "❌ Error: /rekomendasi tidak tersedia saat ini"
            )

    async def daytrade_cmd(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /daytrade command - BPJS single stock analysis."""
        try:
            if not context.args:
                await update.message.reply_text("Gunakan: /daytrade BBCA")
                return

            code = context.args[0].upper()
            await update.message.reply_text(f"🔍 Scanning BPJS untuk {code}...")

            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(None, lambda: BPJSStrategy().analyze(code))

            signal = result.get("entry_signal", {}) or result
            action = signal.get("action", "WAIT")
            emoji = "🟢" if action == "ENTER" else "⏳"

            msg = (
                f"{emoji} *BPJS Day Trade: {code}*\n"
                f"📊 Harga: Rp{result.get('current_price', 0):,.0f}\n"
                f"🎯 Signal: *{action}*\n"
                f"💡 {signal.get('reason', '-')}\n"
            )
            if action == "ENTER":
                msg += (
                    f"💰 Entry: Rp{signal.get('entry_price', 0):,.0f}\n"
                    f"🎯 TP: Rp{signal.get('target_profit', 0):,.0f} (+1.5%)\n"
                    f"🛑 CL: Rp{signal.get('cut_loss', 0):,.0f} (-0.7%)\n"
                )
            msg += f"📊 Volume: {signal.get('volume_ratio', 0):.1f}x | Confidence: {signal.get('confidence', 0)}%\n"
            ff = signal.get("foreign_flow_status", "-")
            msg += f"🌍 Foreign: {ff}\n"
            msg += f"\n🔍 /analyze {code} untuk analisa lengkap"

            await update.message.reply_text(msg, parse_mode="Markdown")
        except Exception as e:
            print(f"Error in daytrade: {e}")
            await update.message.reply_text(
                "❌ Error: /daytrade tidak tersedia saat ini"
            )

    async def daytrade_candidates_cmd(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /bpjs and /daytradecandidates commands."""
        try:
            await update.message.reply_text("🔍 Mencari kandidat BPJS hari ini...")

            loop = asyncio.get_event_loop()
            candidates = await loop.run_in_executor(None, lambda: BPJSStrategy().scan_candidates())

            if not candidates:
                await update.message.reply_text("📭 Tidak ada kandidat BPJS hari ini.")
                return

            msg = "🎯 *BPJS Candidates Hari Ini*\n\n"
            for i, c in enumerate(candidates[:10], 1):
                action = c.get("action", "WAIT")
                emoji = "🟢" if action == "ENTER" else "⏳"
                conf = c.get("confidence", 0)
                msg += f"{emoji} {i}. *{c['stock_code']}* | Conf: {conf}%\n"
                msg += f"   💡 {c.get('reason', '-')[:80]}\n"
            msg += f"\nTotal: {len(candidates)} kandidat"

            await update.message.reply_text(msg, parse_mode="Markdown")
        except Exception as e:
            print(f"Error in bpjs/daytradecandidates: {e}")
            await update.message.reply_text(
                "❌ Error: /bpjs tidak tersedia saat ini"
            )

    async def longterm_cmd(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /longterm command - long term single stock analysis."""
        try:
            if not context.args:
                await update.message.reply_text("Gunakan: /longterm BBCA")
                return

            code = context.args[0].upper()
            await update.message.reply_text(f"🔍 Analisis akumulasi untuk {code}...")

            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(None, lambda: CreativeTraderStrategy().analyze(code))

            acc = result.get("accumulation", {})
            entry = result.get("entry", {})
            tf = result.get("timeframes", {})
            scoring = result.get("scoring", {})

            phase = acc.get("phase", "neutral")
            phase_emoji = {"active_accumulation": "🟢", "early_accumulation": "🟡", "heavy_distribution": "🔴", "early_distribution": "🟠", "neutral": "⚪"}

            action = entry.get("action", "WAIT")
            action_emoji = {"BUY": "🟢", "ACCUMULATE": "🟡", "WAIT": "⏳"}

            msg = (
                f"📈 *Long Term: {code}*\n"
                f"💎 Fase: {phase_emoji.get(phase, '⚪')} {phase.replace('_', ' ').title()}\n"
                f"📊 Akumulasi: {acc.get('accumulation_days', 0)} hari | RS: {acc.get('confidence', 0):.0f}%\n"
                f"💰 Harga: Rp{acc.get('current_price', 0):,.0f}\n"
                f"🎯 Entry: *{action_emoji.get(action, '⏳')} {action}*\n"
                f"💡 {entry.get('reason', '-')}\n"
            )
            if action in ("BUY", "ACCUMULATE"):
                msg += (
                    f"   Entry: Rp{entry.get('entry_price', 0):,.0f}\n"
                    f"   Range: Rp{entry.get('suggested_range', {}).get('min', 0):,.0f} - Rp{entry.get('suggested_range', {}).get('max', 0):,.0f}\n"
                    f"   TP: +6% / +15% | SL: -3%\n"
                )
            msg += (
                f"📅 Timeframe: {tf.get('alignment', '-')}\n"
                f"   Weekly: {tf.get('weekly_outlook', '-')} | Daily: {tf.get('daily_phase', '-')}\n"
            )
            score_val = scoring.get("total_score", 0) if isinstance(scoring, dict) else 0
            if score_val:
                msg += f"📊 Score: {score_val:.0f}/100\n"

            await update.message.reply_text(msg, parse_mode="Markdown")
        except Exception as e:
            print(f"Error in longterm: {e}")
            await update.message.reply_text(
                "❌ Error: /longterm tidak tersedia saat ini"
            )

    async def longtermcandidates_cmd(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /longtermcandidates command - all long term candidates."""
        try:
            await update.message.reply_text("🔍 Mencari kandidat long term...")

            loop = asyncio.get_event_loop()
            candidates = await loop.run_in_executor(None, lambda: CreativeTraderStrategy().scan_for_long_term_candidates())

            if not candidates:
                await update.message.reply_text("📭 Tidak ada kandidat long term saat ini.")
                return

            msg = "💎 *Long Term Candidates*\n\n"
            for i, c in enumerate(candidates[:10], 1):
                phase = c.get("phase", "neutral")
                emoji = {"active_accumulation": "🟢", "early_accumulation": "🟡", "heavy_distribution": "🔴", "early_distribution": "🟠"}.get(phase, "⚪")
                msg += f"{emoji} {i}. *{c['stock_code']}* | Accum: {c.get('accumulation_days', 0)}d | Conf: {c.get('confidence', 0):.0f}%\n"
            msg += f"\nTotal: {len(candidates)} kandidat\nGunakan /longterm BBCA untuk detail"

            await update.message.reply_text(msg, parse_mode="Markdown")
        except Exception as e:
            print(f"Error in longtermcandidates: {e}")
            await update.message.reply_text(
                "❌ Error: /longtermcandidates tidak tersedia saat ini"
            )

    async def broker_cmd(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /broker command - input broker transaction data."""
        try:
            text = update.message.text.strip()
            parts = text.split(None, 1)

            if len(parts) < 2:
                await update.message.reply_text(
                    "Format: /broker BBCA\\`\\`\\`\\ndata broker\\`\\`\\`\\n\\n"
                    "Kirim /brokerhelp untuk panduan.",
                    parse_mode="Markdown",
                )
                return

            stock_code = parts[1].split()[0].upper()
            raw_data = parts[1][len(stock_code):].strip()

            if not raw_data:
                await update.message.reply_text("Data broker kosong. Kirim /brokerhelp untuk panduan.")
                return

            # Remove stock code from the data
            await update.message.reply_text(f"🔍 Memproses data broker {stock_code}...")

            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None, lambda: save_and_analyze_broker_data(stock_code, raw_data)
            )

            if "error" in result:
                await update.message.reply_text(f"❌ {result['error']}")
                return

            await update.message.reply_text(result["summary"], parse_mode="Markdown")

        except Exception as e:
            print(f"Error in broker_cmd: {e}")
            await update.message.reply_text(
                "❌ Error: /broker tidak tersedia saat ini. Kirim /brokerhelp untuk panduan."
            )

    async def brokerhelp_cmd(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /brokerhelp command."""
        try:
            help_text = format_broker_help()
            await update.message.reply_text(help_text, parse_mode="Markdown")
        except Exception as e:
            print(f"Error in brokerhelp: {e}")
            await update.message.reply_text("❌ Error menampilkan bantuan. Coba lagi.")

    async def overview_cmd(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /overview - market summary + AI perf + FGI."""
        try:
            await update.message.reply_text("📊 Ambil overview market...")
            summary = get_market_summary()

            fg = summary["fear_greed"]
            if fg["index"] >= 60:
                fg_emoji = "🟢"
            elif fg["index"] >= 40:
                fg_emoji = "🟡"
            else:
                fg_emoji = "🔴"

            vol = summary.get("total_volume", 0)
            vol_str = f"{vol/1e9:.1f}B" if vol >= 1e9 else f"{vol/1e6:.1f}M"

            adv_pct = (summary["advancing"] / summary["total_stocks"] * 100) if summary["total_stocks"] else 0
            dec_pct = (summary["declining"] / summary["total_stocks"] * 100) if summary["total_stocks"] else 0

            msg = (
                "📊 *Overview Market IDX* 📊\n"
                f"📅 {datetime.now().strftime('%d %b %Y')}\n\n"
                f"{fg_emoji} *Fear & Greed:* {fg['index']} - {fg['label']}\n"
                f"  ◀ Extreme Fear — Extreme Greed ▶\n\n"
                f"📈 Advancing: {summary['advancing']} ({adv_pct:.0f}%)\n"
                f"📉 Declining: {summary['declining']} ({dec_pct:.0f}%)\n"
                f"⏸ Unchanged: {summary['unchanged']}\n"
                f"📊 Total: {summary['total_stocks']} saham\n"
                f"💵 Rata-rata: {summary['avg_change']:+.2f}%\n"
                f"📦 Volume: {vol_str}\n"
                f"🔹 Status: Buka (09:00-15:00 WIB)\n"
            )
            await update.message.reply_text(msg, parse_mode="Markdown")
        except Exception as e:
            print(f"Error in overview: {e}")
            await update.message.reply_text("❌ Error: /overview tidak tersedia")

    async def movers_cmd(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /movers - top gainers, losers, volume."""
        try:
            await update.message.reply_text("📈 Cari market movers...")
            gainers = get_top_gainers(5)
            losers = get_top_losers(5)
            volumes = get_top_volume(5)

            msg = "📈 *Market Movers* 📉\n"
            msg += f"📅 {datetime.now().strftime('%d %b %Y')}\n\n"

            msg += "*🏆 Top Gainers:*\n"
            for g in gainers[:5]:
                msg += f"  {g['code']} — Rp{g['price']:,.0f} ({g['change_pct']:+.2f}%)\n"

            msg += "\n*😞 Top Losers:*\n"
            for g in losers[:5]:
                msg += f"  {g['code']} — Rp{g['price']:,.0f} ({g['change_pct']:+.2f}%)\n"

            msg += "\n*📊 Top Volume:*\n"
            for g in volumes[:5]:
                vol = g.get("volume", 0)
                vol_str = f"{vol/1e9:.2f}B" if vol >= 1e9 else f"{vol/1e6:.1f}M"
                msg += f"  {g['code']} — Rp{g['price']:,.0f} ({vol_str})\n"

            await update.message.reply_text(msg, parse_mode="Markdown")
        except Exception as e:
            print(f"Error in movers: {e}")
            await update.message.reply_text("❌ Error: /movers tidak tersedia")

    async def sectors_cmd(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /sectors - sector performance."""
        try:
            await update.message.reply_text("🏢 Ambil data sektor...")
            sectors = get_sector_performance()

            if not sectors:
                await update.message.reply_text("🏢 Belum ada data sektor.")
                return

            sorted_sectors = sorted(sectors.items(), key=lambda x: -x[1]["performance"])

            msg = "🏢 *Sektor Performance* 🏢\n"
            msg += f"📅 {datetime.now().strftime('%d %b %Y')}\n\n"

            for name, data in sorted_sectors:
                perf = data["performance"]
                icon = "🟢" if perf > 0 else "🔴"
                flow_icon = {"INFLOW": "⬆️", "OUTFLOW": "⬇️", "NEUTRAL": "➡️"}.get(data["flow"], "")
                msg += f"{icon} *{name}*: {perf:+.2f}% {flow_icon}\n"

            await update.message.reply_text(msg, parse_mode="Markdown")
        except Exception as e:
            print(f"Error in sectors: {e}")
            await update.message.reply_text("❌ Error: /sectors tidak tersedia")

    async def predictions_cmd(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /predictions - recent analysis predictions."""
        try:
            await update.message.reply_text("🔮 Ambil prediksi terbaru...")
            history = crud.get_recent_analysis(10)
            alerts = crud.get_alerts(5)

            msg = "🔮 *Prediksi Terbaru* 🔮\n"
            msg += f"📅 {datetime.now().strftime('%d %b %Y')}\n\n"

            if history:
                msg += "*📊 Riwayat Analisa:*\n"
                for h in history[:8]:
                    code = h.get("stock_code", h.get("stock", "?"))
                    signal = h.get("signal", h.get("recommendation", "-"))
                    conf = h.get("confidence", h.get("score", 0))
                    msg += f"  • {code}: {signal} ({conf}%)\n"
            else:
                msg += "Belum ada riwayat analisa.\n"

            if alerts:
                msg += "\n*⚠️ Alert:*\n"
                for a in alerts[:3]:
                    msg += f"  • {a.get('stock_code', '?')}: {a.get('message', a.get('alert_type', ''))}\n"

            msg += "\n💡 Gunakan /analyze BBCA untuk analisa baru"
            await update.message.reply_text(msg, parse_mode="Markdown")
        except Exception as e:
            print(f"Error in predictions: {e}")
            await update.message.reply_text("❌ Error: /predictions tidak tersedia")

    async def marketreport_cmd(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Hidden: show latest @creativetrader report + AI analysis."""
        try:
            await update.message.reply_text("📊 Ambil laporan pasar terbaru...")
            import json, os
            base = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
            reports_file = os.path.join(base, "market_reports.json")
            if not os.path.exists(reports_file):
                await update.message.reply_text("❌ Belum ada data. Jalankan scraper dulu.")
                return
            with open(reports_file) as f:
                reports = json.load(f)
            if not reports:
                await update.message.reply_text("❌ Laporan kosong.")
                return
            latest = reports[0]
            date = latest.get('date', '?')
            ihsg = latest.get('ihsg_change')
            fb = latest.get('foreign_buy', [])
            lb = latest.get('local_buy', [])
            gainers = latest.get('gainer', [])
            losers = latest.get('loser', [])
            ihsg_icon = "🔴" if (ihsg or 0) < 0 else "🟢"
            msg = f"{ihsg_icon} *Market Report* — {date}\nIHSG: {ihsg:+.2f}%\n\n"
            if fb:
                msg += "*🌍 Top Foreign Buy:*\n"
                for s in fb[:5]:
                    v = s['value']
                    u = "T" if v >= 1e12 else "M"
                    w = v / 1e12 if v >= 1e12 else v / 1e9
                    msg += f"  {s['stock']}: Rp{w:.2f}{u}\n"
                msg += "\n"
            if lb:
                msg += "*🏠 Top Local Buy:*\n"
                for s in lb[:5]:
                    v = s['value']
                    u = "T" if v >= 1e12 else "M"
                    w = v / 1e12 if v >= 1e12 else v / 1e9
                    msg += f"  {s['stock']}: Rp{w:.2f}{u}\n"
                msg += "\n"
            if gainers:
                msg += "*📈 Top Gainer:*\n"
                for g in gainers[:3]:
                    msg += f"  {g['stock']}: {g['change_pct']:+.1f}%\n"
            if losers:
                msg += "*📉 Top Loser:*\n"
                for l in losers[:3]:
                    msg += f"  {l['stock']}: {l['change_pct']:+.1f}%\n"
            msg += "\n"
            # AI analysis
            from collections import Counter
            ihsg_vals = [r['ihsg_change'] for r in reports if r['ihsg_change'] is not None]
            red = sum(1 for v in ihsg_vals if v < 0)
            green = sum(1 for v in ihsg_vals if v > 0)
            avg = sum(ihsg_vals) / len(ihsg_vals) if ihsg_vals else 0
            foreign_freq = Counter()
            for r in reports:
                for s in r.get('foreign_buy', []):
                    foreign_freq[s['stock']] += 1
            top_fb = foreign_freq.most_common(5)
            msg += f"*📊 Analisis ({len(reports)} laporan)*\n"
            msg += f"Rata IHSG: {avg:+.2f}% | Hijau/Merah: {green}/{red}\n"
            msg += f"Top asing beli: {', '.join(s for s, c in top_fb)}\n"
            msg += f"\n💡 /analyze BBCA — analisa detail"
            await update.message.reply_text(msg, parse_mode="Markdown")
        except Exception as e:
            print(f"Error in marketreport: {e}")
            await update.message.reply_text("❌ Error: /marketreport tidak tersedia")

    def _scan_buy_list(self):
        """Scan all stocks and return BUY candidates. Runs in thread."""
        all_codes = list(STOCK_LIST.keys())[:20]
        buy_list = []
        for code in all_codes:
            try:
                result = self.analysis_service.analyze_stock(code, use_ai=True)
                if "error" in result:
                    continue
                rec = result.get("recommendation", "HOLD")
                conf = result.get("confidence", 0)
                if rec == "BUY" and conf >= 50:
                    buy_list.append({
                        "code": code,
                        "name": result.get("stock_name", code),
                        "price": result.get("price", 0),
                        "change_pct": result.get("change_pct", 0),
                        "confidence": conf,
                        "rsi": result.get("rsi", 0),
                        "rsi_status": result.get("rsi_status", ""),
                        "trend": result.get("trend", ""),
                        "reason": result.get("reason", ""),
                        "source": result.get("source", ""),
                    })
            except Exception:
                continue
        return buy_list

    async def error_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle uncaught errors from any handler."""
        print(f"Telegram error: {context.error}")
        if update and update.effective_message:
            await update.effective_message.reply_text(
                "❌ Terjadi kesalahan. Silakan coba lagi."
            )

    async def set_commands(self, app: Application) -> None:
        """Register bot command list with Telegram."""
        commands = [
            BotCommand("start", "Mulai bot"),
            BotCommand("help", "Bantuan & daftar perintah"),
            BotCommand("analyze", "Analisa saham (contoh: /analyze BBCA)"),
            BotCommand("add", "Tambah saham ke watchlist"),
            BotCommand("remove", "Hapus saham dari watchlist"),
            BotCommand("watchlist", "Lihat watchlist Anda"),
            BotCommand("topgainer", "Top gainer hari ini"),
            BotCommand("toploser", "Top loser hari ini"),
            BotCommand("topvolume", "Top volume perdagangan"),
            BotCommand("market", "Ringkasan market IDX"),
            BotCommand("sentiment", "Sentimen market"),
            BotCommand("feedback", "Kirim feedback"),
            BotCommand("accuracy", "Akurasi prediksi"),
            BotCommand("performance", "Performa portofolio"),
            BotCommand("strategy", "Strategi rekomendasi"),
            BotCommand("rekomendasi", "Rekomendasi saham beli besok"),
            BotCommand("daytrade", "BPJS Day Trade (contoh: /daytrade BBCA)"),
            BotCommand("bpjs", "Kandidat BPJS hari ini"),
            BotCommand("daytradecandidates", "Kandidat BPJS (alias /bpjs)"),
            BotCommand("longterm", "Long term akumulasi (contoh: /longterm BBCA)"),
            BotCommand("longtermcandidates", "Kandidat long term"),
            BotCommand("broker", "Input data broker asing (contoh: /broker BBCA)"),
            BotCommand("brokerhelp", "Panduan input data broker"),
            BotCommand("overview", "Overview market IDX"),
            BotCommand("movers", "Top gainers/losers/volume"),
            BotCommand("sectors", "Performa sektor"),
            BotCommand("predictions", "Prediksi & alert terbaru"),
        ]
        await app.bot.set_my_commands(commands)

        await self._send_startup_notification(app)

    async def _send_startup_notification(self, app: Application) -> None:
        """Send startup notification to all active users."""
        telegram_ids = crud.get_telegram_ids()
        if not telegram_ids:
            return
        now = datetime.now().strftime("%d-%b-%Y %H:%M")
        msg = (
            f"✅ *AI Stock Analyzer Aktif*\n\n"
            f"Bot telah berhasil diaktifkan.\n"
            f"📅 {now}\n\n"
            f"Gunakan /help untuk melihat daftar perintah."
        )
        for tid in telegram_ids:
            try:
                await app.bot.send_message(chat_id=tid, text=msg, parse_mode="Markdown")
            except Exception:
                pass

    def run(self):
        """Start the Telegram bot polling."""
        if not self.token:
            print("⚠️ TELEGRAM_BOT_TOKEN tidak dikonfigurasi. Bot Telegram tidak akan aktif.")
            return

        asyncio.set_event_loop(asyncio.new_event_loop())
        self.app = Application.builder().token(self.token).post_init(self.set_commands).build()

        self.app.add_handler(CommandHandler("start", self.start))
        self.app.add_handler(CommandHandler("help", self.help_command))
        self.app.add_handler(CommandHandler("analyze", self.analyze))
        self.app.add_handler(CommandHandler("add", self.add_watchlist))
        self.app.add_handler(CommandHandler("remove", self.remove_watchlist))
        self.app.add_handler(CommandHandler("watchlist", self.watchlist))
        self.app.add_handler(CommandHandler("topgainer", self.top_gainer))
        self.app.add_handler(CommandHandler("toploser", self.top_loser))
        self.app.add_handler(CommandHandler("topvolume", self.top_volume))
        self.app.add_handler(CommandHandler("market", self.market))
        self.app.add_handler(CommandHandler("sentiment", self.sentiment))
        self.app.add_handler(CommandHandler("feedback", self.feedback_cmd))
        self.app.add_handler(CommandHandler("accuracy", self.accuracy_cmd))
        self.app.add_handler(CommandHandler("performance", self.performance_cmd))
        self.app.add_handler(CommandHandler("strategy", self.strategy_cmd))
        self.app.add_handler(CommandHandler("rekomendasi", self.rekomendasi_cmd))
        self.app.add_handler(CommandHandler("daytrade", self.daytrade_cmd))
        self.app.add_handler(CommandHandler("bpjs", self.daytrade_candidates_cmd))
        self.app.add_handler(CommandHandler("daytradecandidates", self.daytrade_candidates_cmd))
        self.app.add_handler(CommandHandler("longterm", self.longterm_cmd))
        self.app.add_handler(CommandHandler("longtermcandidates", self.longtermcandidates_cmd))
        self.app.add_handler(CommandHandler("broker", self.broker_cmd))
        self.app.add_handler(CommandHandler("brokerhelp", self.brokerhelp_cmd))
        self.app.add_handler(CommandHandler("marketreport", self.marketreport_cmd))  # hidden
        self.app.add_handler(CommandHandler("overview", self.overview_cmd))
        self.app.add_handler(CommandHandler("movers", self.movers_cmd))
        self.app.add_handler(CommandHandler("sectors", self.sectors_cmd))
        self.app.add_handler(CommandHandler("predictions", self.predictions_cmd))
        self.app.add_error_handler(self.error_handler)

        print("🤖 Telegram Bot started...")
        self.app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    bot = TelegramBot()
    bot.run()
