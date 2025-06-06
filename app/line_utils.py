from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError, LineBotApiError
from linebot.models import TextSendMessage
import os
import hashlib
import hmac
import base64
import requests
from dotenv import load_dotenv
import logging

# โหลด environment variables
load_dotenv()

logger = logging.getLogger(__name__)

class LineBot:
    def __init__(self):
        self.channel_access_token = os.getenv("LINE_CHANNEL_ACCESS_TOKEN")
        self.channel_secret = os.getenv("LINE_CHANNEL_SECRET")
        
        if not self.channel_access_token:
            raise ValueError("LINE_CHANNEL_ACCESS_TOKEN is required")
        if not self.channel_secret:
            raise ValueError("LINE_CHANNEL_SECRET is required")
            
        self.line_bot_api = LineBotApi(self.channel_access_token)
        self.handler = WebhookHandler(self.channel_secret)
        
        # สร้างโฟลเดอร์สำหรับเก็บภาพ
        try:
            os.makedirs("static/slips", exist_ok=True)
            os.makedirs("logs", exist_ok=True)
        except PermissionError:
            print("Warning: Cannot create directories, using current directory")
    
    def verify_signature(self, body: bytes, signature: str) -> bool:
        """ตรวจสอบ signature จาก LINE"""
        if not signature:
            return False
            
        try:
            expected_signature = hmac.new(
                self.channel_secret.encode('utf-8'),
                body,
                hashlib.sha256
            ).digest()
            expected_signature = base64.b64encode(expected_signature).decode('utf-8')
            return hmac.compare_digest(signature, expected_signature)
        except Exception as e:
            logger.error(f"Signature verification error: {str(e)}")
            return False
    
    async def download_image(self, message_id: str, user_id: str) -> str:
        """ดาวน์โหลดภาพจาก LINE และบันทึกลงไฟล์"""
        try:
            # ดาวน์โหลดภาพ
            message_content = self.line_bot_api.get_message_content(message_id)
            
            # สร้างชื่อไฟล์
            filename = f"slip_{user_id}_{message_id}.jpg"
            
            # เลือกโฟลเดอร์สำหรับเก็บไฟล์
            try:
                os.makedirs("static/slips", exist_ok=True)
                filepath = os.path.join("static/slips", filename)
            except PermissionError:
                # ถ้าไม่สามารถสร้างโฟลเดอร์ได้ ให้เก็บในโฟลเดอร์ปัจจุบัน
                filepath = filename
            
            # บันทึกไฟล์
            with open(filepath, 'wb') as f:
                for chunk in message_content.iter_content():
                    f.write(chunk)
            
            logger.info(f"Image saved: {filepath}")
            return filepath
            
        except LineBotApiError as e:
            logger.error(f"Error downloading image: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error downloading image: {str(e)}")
            raise
    
    async def reply_text(self, reply_token: str, text: str):
        """ตอบกลับข้อความ"""
        try:
            message = TextSendMessage(text=text)
            self.line_bot_api.reply_message(reply_token, message)
            logger.info(f"Reply sent: {text[:50]}...")
        except LineBotApiError as e:
            logger.error(f"Error sending reply: {str(e)}")
            raise
    
    async def push_text(self, user_id: str, text: str):
        """ส่งข้อความแบบ push"""
        try:
            message = TextSendMessage(text=text)
            self.line_bot_api.push_message(user_id, message)
            logger.info(f"Push message sent to {user_id}: {text[:50]}...")
        except LineBotApiError as e:
            logger.error(f"Error sending push message: {str(e)}")
            raise

def generate_help_message():
    return """🆘 วิธีใช้งsaddddddddddddddาน\n..."""
