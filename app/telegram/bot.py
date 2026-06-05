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
from app.services.market_service import get_market_summary, get_market_sentiment
from app.charts.chart_generator import generate_full_analysis_chart
from app.database import crud
from app.database import ai_crud
from app.ai.learning_engine import LearningEngine


class TelegramBot:
    def __init__(self):
        self.token = Config.TELEGRAM_BOT_TOKEN
        self.app = None
        self.analysis_service = AnalysisService()
        self.learning = LearningEngine()

    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
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
             f"/daytrade-candidates - Kandidat BPJS hari ini\n"
             f"/feedback benar BBCA - Beri feedback\n"
             f"/accuracy - Skor AI\n"
             f"/performance - Performa AI\n"
             f"/strategy - Mode strategi\n"
             f"/help - Bantuan\n\n"
            f"Contoh: /analyze BBCA",
            parse_mode="Markdown",
        )

    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await update.message.reply_text(
            "📚 *Bantuan AI Stock Analyzer*\n\n"
            "*Analisa Saham:*\n"
            "/analyze BBCA - Analisa detail + chart\n\n"
            "*Watchlist:*\n"
            "/add BBCA - Tambah saham\n"
            "/remove BBCA - Hapus saham\n"
            "/watchlist - Daftar watchlist\n\n"
            "*Market:*\n"
            "/topgainer - Top gainer\n"
            "/toploser - Top loser\n"
            "/topvolume - Top volume\n"
            "/market - Overview market\n"
            "/sentiment - Sentimen market\n"
            "/rekomendasi - Rekomendasi beli besok\n"
            "/daytrade BBCA - BPJS Day Trade signal\n"
            "/daytrade-candidates - Kandidat BPJS hari ini\n\n"
            "*Saham tersedia:*\n"
            f"{', '.join(sorted(STOCK_LIST.keys())[:10])}\n"
            "dan lainnya...",
            parse_mode="Markdown",
        )

    async def analyze(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not context.args:
            await update.message.reply_text("Gunakan: /analyze BBCA")
            return

        code = context.args[0].upper()
        await update.message.reply_text(f"🔍 Menganalisa {code}...")

        # Run analysis in thread pool
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            None, lambda: self.analysis_service.analyze_stock(code, use_ai=True)
        )

        if "error" in result:
            await update.message.reply_text(f"❌ {result['error']}")
            return

        # Generate chart
        chart_path = None
        df = result.get("dataframe")
        if df is not None:
            try:
                chart_path = generate_full_analysis_chart(
                    df, result["stock_code"], result.get("stock_name", "")
                )
            except Exception as e:
                print(f"Chart error: {e}")

        # Format response
        emoji = {"BUY": "🟢", "HOLD": "🟡", "SELL": "🔴"}
        rec_emoji = emoji.get(result["recommendation"], "⚪")
        
        # Source indicator
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

        # Send chart
        if chart_path and os.path.exists(chart_path):
            with open(chart_path, "rb") as f:
                await update.message.reply_photo(
                    photo=f,
                    caption=f"Chart {result['stock_code']} - {result['trend']} | Rec: {result['recommendation']} ({result['confidence']}%)",
                )

    async def add_watchlist(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not context.args:
            await update.message.reply_text("Gunakan: /add BBCA")
            return

        code = context.args[0].upper()
        user = crud.get_user(update.effective_user.id)
        if not user:
            user = crud.add_user(update.effective_user.id, update.effective_user.username)

        crud.add_to_watchlist(user["id"], code, STOCK_LIST.get(code, ""))
        await update.message.reply_text(f"✅ {code} ditambahkan ke watchlist!")

    async def remove_watchlist(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not context.args:
            await update.message.reply_text("Gunakan: /remove BBCA")
            return

        code = context.args[0].upper()
        user = crud.get_user(update.effective_user.id)
        if user:
            crud.remove_from_watchlist(user["id"], code)

        await update.message.reply_text(f"🗑 {code} dihapus dari watchlist!")

    async def watchlist(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
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

    async def top_gainer(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await update.message.reply_text("📈 Mengambil data top gainer...")
        gainers = get_top_gainers(10)

        message = "📈 *Top Gainer Hari Ini:*\n\n"
        for i, g in enumerate(gainers, 1):
            message += f"{i}. {g['code']} - Rp{g['price']:,.0f} ({g['change_pct']:+.2f}%)\n"

        await update.message.reply_text(message, parse_mode="Markdown")

    async def top_loser(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await update.message.reply_text("📉 Mengambil data top loser...")
        losers = get_top_losers(10)

        message = "📉 *Top Loser Hari Ini:*\n\n"
        for i, g in enumerate(losers, 1):
            message += f"{i}. {g['code']} - Rp{g['price']:,.0f} ({g['change_pct']:+.2f}%)\n"

        await update.message.reply_text(message, parse_mode="Markdown")

    async def top_volume(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await update.message.reply_text("📊 Mengambil data top volume...")
        volumes = get_top_volume(10)

        message = "📊 *Top Volume Hari Ini:*\n\n"
        for i, g in enumerate(volumes, 1):
            message += f"{i}. {g['code']} - {g['volume']:,} lembar\n"

        await update.message.reply_text(message, parse_mode="Markdown")

    async def market(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
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

    async def sentiment(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
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

    async def feedback_cmd(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
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

    async def accuracy_cmd(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
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

    async def performance_cmd(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
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

    async def strategy_cmd(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
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

    async def rekomendasi_cmd(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await update.message.reply_text("🔍 Mencari rekomendasi saham untuk besok...")

        # Run heavy analysis in thread pool to avoid blocking event loop
        loop = asyncio.get_event_loop()
        buy_list = await loop.run_in_executor(None, self._scan_buy_list)

        if not buy_list:
            await update.message.reply_text(
                "📭 *Tidak ada rekomendasi BUY untuk besok.*\n\n"
                "Semua saham dalam HOLD/SELL.",
                parse_mode="Markdown"
            )
            return

        # Sort by confidence
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
        print(f"Telegram error: {context.error}")
        if update and update.effective_message:
            await update.effective_message.reply_text(
                "❌ Terjadi kesalahan. Silakan coba lagi."
            )

    async def set_commands(self, app: Application) -> None:
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
            BotCommand("daytrade", "BPJS Day Trade signal (contoh: /daytrade BBCA)"),
            BotCommand("daytrade-candidates", "Kandidat BPJS hari ini"),
        ]
        await app.bot.set_my_commands(commands)

        await self._send_startup_notification(app)

    async def _send_startup_notification(self, app: Application) -> None:
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
        self.app.add_error_handler(self.error_handler)

        print("🤖 Telegram Bot started...")
        self.app.run_polling(allowed_updates=Update.ALL_TYPES)
 