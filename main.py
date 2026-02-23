import time
import re
import requests
from astrbot.api.all import *
from .utils import decode_base64_url, extract_card_key
from .captcha_solver import bypass_captcha

class CardKeyGetter(Star):
    def __init__(self, context: Context):
        super().__init__(context)
        self.enable_auto_detect = True
        self.auto_detect_domains = [
            "auth.platorelay.com",
            "auth.platoboost.com",
            "auth.platoboost.app",
            "auth.platoboost.net",
            "deltaios-executor.com"
        ]

    @event_message_type(EventMessageType.ALL)
    async def on_event(self, event: AstrMessageEvent):
        if event.message_str.startswith('/getkey'):
            await self.handle_getkey(event)
            return

        if self.enable_auto_detect and event.is_group:
            for domain in self.auto_detect_domains:
                pattern = rf'https?://{re.escape(domain)}[^\s]+'
                match = re.search(pattern, event.message_str)
                if match:
                    raw_url = match.group()
                    await self.process_url(event, raw_url)
                    return

    async def handle_getkey(self, event: AstrMessageEvent):
        parts = event.message_str.strip().split(maxsplit=1)
        if len(parts) < 2:
            yield event.make_result().message("请提供链接，例如：/getkey https://auth.platorelay.com/a?d=...")
            return
        raw_url = parts[1].strip()
        await self.process_url(event, raw_url)

    async def process_url(self, event: AstrMessageEvent, raw_url: str):
        start_time = time.time()
        yield event.make_result().message(f"⏳ 自动检测到 Plato 链接，开始解析: {raw_url}")

        session = requests.Session()
        session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        })

        try:
            target_url = decode_base64_url(raw_url)
            yield event.make_result().message(f"🔍 目标地址: {target_url}")

            resp = session.get(target_url, timeout=15)
            if resp.status_code != 200:
                elapsed = time.time() - start_time
                yield event.make_result().message(f"❌ 页面访问失败，状态码: {resp.status_code}（耗时 {elapsed:.2f} 秒）")
                return

            if 'sentry' in resp.url or 'captcha' in resp.text.lower():
                yield event.make_result().message("🛡️ 检测到验证码，尝试绕过...")
                try:
                    session = bypass_captcha(session)
                except Exception as e:
                    elapsed = time.time() - start_time
                    yield event.make_result().message(f"❌ 验证码绕过失败: {e}（耗时 {elapsed:.2f} 秒）")
                    return
                resp = session.get(target_url, timeout=15)
                if resp.status_code != 200:
                    elapsed = time.time() - start_time
                    yield event.make_result().message(f"❌ 验证后页面访问失败，状态码: {resp.status_code}（耗时 {elapsed:.2f} 秒）")
                    return

            card_key = extract_card_key(resp.text)
            elapsed = time.time() - start_time
            if card_key:
                yield event.make_result().message(f"✅ 获取到卡密：{card_key}（耗时 {elapsed:.2f} 秒）")
            else:
                yield event.make_result().message(f"❌ 未能在页面中找到卡密，请检查链接或调整解析规则。（耗时 {elapsed:.2f} 秒）")

        except Exception as e:
            elapsed = time.time() - start_time
            yield event.make_result().message(f"❌ 处理过程中发生异常: {e}（耗时 {elapsed:.2f} 秒）")
