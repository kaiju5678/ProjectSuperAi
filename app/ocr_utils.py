# app/ocr_utils.py - EasyOCR Version (แก้ไขแล้ว)
import easyocr
import re
from datetime import datetime
from typing import Dict, Any, Optional
import logging

# ตั้งค่า logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# สร้าง EasyOCR reader (รองรับภาษาไทยและอังกฤษ)
reader = easyocr.Reader(['th', 'en'], gpu=False)

def extract_text_from_image(image_path: str) -> str:
    """
    แยกข้อความจากรูปภาพด้วย EasyOCR
    
    Args:
        image_path (str): path ของไฟล์รูปภาพ
        
    Returns:
        str: ข้อความที่อ่านได้
    """
    try:
        logger.info(f"กำลังอ่านรูปภาพ: {image_path}")
        
        # อ่านข้อความจากรูป
        results = reader.readtext(image_path)
        
        # รวมข้อความทั้งหมด
        extracted_text = ""
        for (bbox, text, confidence) in results:
            # กรองข้อความที่มี confidence สูงกว่า 0.5
            if confidence > 0.5:
                extracted_text += text + "\n"
        
        logger.info(f"อ่านข้อความสำเร็จ: {len(extracted_text)} ตัวอักษร")
        return extracted_text.strip()
        
    except Exception as e:
        logger.error(f"Error extracting text: {str(e)}")
        raise Exception(f"ไม่สามารถอ่านข้อความจากรูปได้: {str(e)}")

def parse_payment_slip(text: str) -> Dict[str, Any]:
    """
    แยกข้อมูลสลิปเงินจากข้อความ
    
    Args:
        text (str): ข้อความที่อ่านได้จากรูป
        
    Returns:
        Dict: ข้อมูลที่แยกได้
    """
    try:
        parsed_data = {
            "amount": None,
            "date": None,
            "time": None,
            "bank": None,
            "reference": None,
            "account_number": None,
            "recipient": None,
            "sender": None,
            "raw_text": text
        }
        
        # แยกจำนวนเงิน - ปรับปรุงให้จับได้ดีขึ้น
        amount_patterns = [
            r'([0-9,]+\.?[0-9]*)\s*บาท',
            r'([0-9,]+\.?[0-9]*)\s*THB',
            r'จำนวนเงิน[:\s]*([0-9,]+\.?[0-9]*)',
            r'Amount[:\s]*([0-9,]+\.?[0-9]*)',
            r'฿([0-9,]+\.?[0-9]*)',
            r'^\s*([0-9,]+\.?[0-9]*)\s*$'  # เลขที่อยู่คนเดียวในบรรทัด
        ]
        
        # หาจำนวนเงินจากทุกบรรทัด
        lines = text.split('\n')
        for line in lines:
            line = line.strip()
            for pattern in amount_patterns:
                match = re.search(pattern, line, re.IGNORECASE)
                if match:
                    amount_candidate = match.group(1).replace(',', '')
                    # ตรวจสอบว่าเป็นตัวเลขที่สมเหตุสมผล (มากกว่า 0)
                    try:
                        amount_num = float(amount_candidate)
                        if amount_num > 0:
                            parsed_data["amount"] = amount_candidate
                            break
                    except:
                        continue
            if parsed_data["amount"]:
                break
        
        # แยกวันที่ - ปรับปรุงให้จับภาษาไทยได้ดีขึ้น
        date_patterns = [
            r'(\d{1,2}\s+(?:ม\.ค\.|ก\.พ\.|มี\.ค\.|เม\.ย\.|พ\.ค\.|มิ\.ย\.|ก\.ค\.|ส\.ค\.|ก\.ย\.|ต\.ค\.|พ\.ย\.|ธ\.ค\.)\s+\d{4})',
            r'(\d{1,2}\s+(?:มกราคม|กุมภาพันธ์|มีนาคม|เมษายน|พฤษภาคม|มิถุนายน|กรกฎาคม|สิงหาคม|กันยายน|ตุลาคม|พฤศจิกายน|ธันวาคม)\s+\d{4})',
            r'(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})',
            r'(\d{4}-\d{2}-\d{2})',
            r'(\d{2}/\d{2}/\d{4})'
        ]
        
        for pattern in date_patterns:
            match = re.search(pattern, text)
            if match:
                parsed_data["date"] = match.group(1)
                break
        
        # แยกเวลา
        time_patterns = [
            r'(\d{1,2}:\d{2}:\d{2})',
            r'(\d{1,2}:\d{2})'
        ]
        
        for pattern in time_patterns:
            match = re.search(pattern, text)
            if match:
                parsed_data["time"] = match.group(1)
                break
        
        # แยกชื่อธนาคาร - เพิ่ม SCB เป็นพิเศษ
        bank_keywords = {
            'SCB': ['scb', 'uscb', 'ไทยพาณิชย์', 'siam commercial'],
            'กสิกรไทย': ['กสิกรไทย', 'kbank', 'kasikorn'],
            'กรุงเทพ': ['กรุงเทพ', 'bbl', 'bangkok bank'],
            'กรุงไทย': ['กรุงไทย', 'ktb', 'krung thai'],
            'ทีเอ็มบี': ['ทีเอ็มบี', 'tmb', 'tmbthanachart'],
            'ธนชาต': ['ธนชาต', 'thanachart'],
            'ยูโอบี': ['ยูโอบี', 'uob'],
            'ซีไอเอ็มบี': ['ซีไอเอ็มบี', 'cimb'],
            'ไอซีบีซี': ['ไอซีบีซี', 'icbc'],
            'ก.ส.ห.': ['ก.ส.ห.', 'baac', 'bank for agriculture']
        }
        
        text_lower = text.lower()
        for bank_name, keywords in bank_keywords.items():
            for keyword in keywords:
                if keyword.lower() in text_lower:
                    parsed_data["bank"] = bank_name
                    break
            if parsed_data["bank"]:
                break
        
        # รองรับสลิปกรุงไทย
        ktb_pattern = (
            r'(?:นาย|นาง|น\.ส\.|ด\.ช\.|ด\.ญ\.)\s*([^\n]+)\s*\n'
            r'(?:กรุงไทย|krungthai)\s*\n'
            r'xxx-x-[x\d]+-\d\s*\n'
            r'รหัสร้านค้า\s*\n'
            r'(\d+)\s*\n'
            r'(?:รหัสธุรกรรม|เลขที่อ้างอิง)\s*\n'
            r'[a-zA-Z0-9]+\s*\n'
            r'จำนวนเงิน\s*\n'
            r'(\d+(?:\.\d{2})?)\s*บาท'
        )
        match = re.search(ktb_pattern, text, re.IGNORECASE | re.MULTILINE)
        if match:
            sender_name = match.group(1).strip()
            parsed_data["sender"] = sender_name
            parsed_data["amount"] = match.group(3)
            store_id = match.group(2)
            return parsed_data

        # รองรับสลิปกสิกรไทย - แก้ไขใหม่
        kbank_pattern = r'นาย\s+([^\n]+)\s*\nธ\.กสิกรไทย[\s\S]*?นาง\s+([^\n]+)\s*\nธ\.กสิกรไทย'
        match = re.search(kbank_pattern, text)
        if match:
            parsed_data["sender"] = f"นาย {match.group(1)}".strip()  # เพิ่ม "นาย" ในผู้โอน
            parsed_data["recipient"] = f"นาง {match.group(2)}".strip()
            return parsed_data

        # แยกผู้โอน - ปรับปรุงให้จับได้ดีขึ้น
        sender_patterns = [
            r'จาก\s*\n\s*(นาย\s+[^\n]+)',  # แก้ไขให้เก็บคำนำหน้า "นาย" ด้วย
            r'จาก\s*\n\s*(นาง\s+[^\n]+)', 
            r'จาก\s*\n\s*(นางสาว\s+[^\n]+)',
            r'จาก\s*\n\s*([^\n]+?)(?=\s*xxx|\s*x-|\n|$)',
            r'(นาย\s+[^\n]+?)(?=\s*xxx|\s*x-|\n|$)',  # แก้ไขให้เก็บคำนำหน้า "นาย" ด้วย
            r'(นาง\s+[^\n]+?)(?=\s*xxx|\s*x-|\n|$)',
            r'(นางสาว\s+[^\n]+?)(?=\s*xxx|\s*x-|\n|$)',
            r'ผู้โอน[:\s]*([^\n]+)',
            r'from[:\s]*([^\n]+)'
        ]
        
        for pattern in sender_patterns:
            match = re.search(pattern, text, re.IGNORECASE | re.MULTILINE)
            if match:
                sender = match.group(1).strip()
                # ทำความสะอาดชื่อ
                sender = re.sub(r'\s*xxx.*', '', sender).strip()
                sender = re.sub(r'\s*x-.*', '', sender).strip()
                if sender and len(sender) > 1:  # ตรวจสอบว่าไม่ใช่ข้อความว่าง
                    parsed_data["sender"] = sender  # ไม่ต้องเพิ่ม f"นาย {sender}" แล้ว
                    break

        # แยกผู้รับ - ปรับปรุงให้จับได้ดีขึ้น
        recipient_patterns = [
            r'ไปยัง\s*\n\s*บจก\.\s*\n\s*([^\n]+?)(?=\s*x-|\n|$)',
            r'ไปยัง\s*\n\s*([^\n]+?)(?=\s*x-|\n|$)',
            r'บจก\.\s*\n\s*([^\n]+?)(?=\s*x-|\n|$)',
            r'บจก\.\s*([^\n]+?)(?=\s*x-|\n|$)',
            r'ผู้รับ[:\s]*([^\n]+)',
            r'to[:\s]*([^\n]+)',
            r'นาย\s+([^\n]+?)(?=\s*xxx|\s*x-|\n|$)',
            r'นาง\s+([^\n]+?)(?=\s*xxx|\s*x-|\n|$)',
        ]
        
        for pattern in recipient_patterns:
            match = re.search(pattern, text, re.IGNORECASE | re.MULTILINE)
            if match:
                recipient = match.group(1).strip()
                # ทำความสะอาดชื่อ
                recipient = re.sub(r'\s*x-.*', '', recipient).strip()
                recipient = re.sub(r'\s*xxx.*', '', recipient).strip()
                if recipient and len(recipient) > 1:  # ตรวจสอบว่าไม่ใช่ข้อความว่าง
                    parsed_data["recipient"] = recipient
                    break
        
        # แยกหมายเลขอ้างอิง - ปรับปรุงให้จับได้ดีขึ้น
        ref_patterns = [
            r'รหัสอ้างอิง[:\s]*([A-Za-z0-9]+)',
            r'อ้างอิง[:\s]*([A-Za-z0-9]+)',
            r'reference[:\s]*([A-Za-z0-9]+)',
            r'ref[:\s]*([A-Za-z0-9]+)',
            r'เลขที่[:\s]*([A-Za-z0-9]+)'
        ]
        
        for pattern in ref_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                parsed_data["reference"] = match.group(1)
                break
        
        # แยกเลขบัญชี
        account_patterns = [
            r'(xxx-xxx\d+-\d+)',
            r'(x-\d+)',
            r'บัญชี[:\s]*([0-9x-]+)',
            r'account[:\s]*([0-9x-]+)',
            r'a/c[:\s]*([0-9x-]+)'
        ]
        
        for pattern in account_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                parsed_data["account_number"] = match.group(1)
                break
        
        return parsed_data
        
    except Exception as e:
        logger.error(f"Error parsing slip: {str(e)}")
        return {"raw_text": text, "error": str(e)}

def format_slip_summary(data) -> str:
    """
    จัดรูปแบบข้อมูลสลิปเงิน - รองรับทั้ง text และ parsed_data
    
    Args:
        data: ข้อความ (str) หรือข้อมูลที่แยกแล้ว (dict)
        
    Returns:
        str: ข้อความสรุปที่จัดรูปแบบแล้ว
    """
    try:
        # ตรวจสอบว่า input เป็น dict หรือ string
        if isinstance(data, dict):
            parsed_data = data
            text = data.get('raw_text', '')
        else:
            # ถ้าเป็น string ให้แยกข้อมูลก่อน
            text = data
            parsed_data = parse_payment_slip(text)
        
        summary = "📄 **สรุปข้อมูลสลิป**\n"
        
        # ผู้โอน
        if parsed_data.get("sender"):
            summary += f"👤 **ผู้โอน**: {parsed_data['sender']}\n"
        
        # ผู้รับ
        if parsed_data.get("recipient"):
            summary += f"👥 **ผู้รับ**: {parsed_data['recipient']}\n"
        
        # จำนวนเงิน
        if parsed_data.get("amount"):
            amount = parsed_data["amount"]
            try:
                # แปลงเป็นตัวเลขแล้วจัดรูปแบบ
                amount_num = float(amount.replace(',', ''))
                summary += f"💰 **จำนวนเงิน**: {amount_num:,.2f} บาท\n"
            except:
                summary += f"💰 **จำนวนเงิน**: {amount} บาท\n"
        
        # เวลา
        if parsed_data.get("time"):
            summary += f"⏰ **เวลา**: {parsed_data['time']}\n"
        
        # ธนาคาร
        if parsed_data.get("bank"):
            summary += f"🏦 **ธนาคาร**: {parsed_data['bank']}\n"
        
        # หมายเลขอ้างอิง
        if parsed_data.get("reference"):
            summary += f"🔢 **หมายเลขอ้างอิง**: {parsed_data['reference']}\n"
        
        # วันที่ (ถ้ามี)
        if parsed_data.get("date"):
            summary += f"📅 **วันที่**: {parsed_data['date']}\n"
        
        # เลขบัญชี (ถ้ามี)
        if parsed_data.get("account_number"):
            summary += f"💳 **เลขบัญชี**: {parsed_data['account_number']}\n"
        
        # ข้อความเต็ม
        raw_text = parsed_data.get('raw_text', text if isinstance(data, str) else 'ไม่มีข้อมูล')
        summary += f"📝 **ข้อความเต็ม**:\n```\n{raw_text}\n```\n"
        
        # สถิติ
        char_count = len(raw_text)
        line_count = len(raw_text.split('\n'))
        summary += f"📝 **จำนวนตัวอักษร:** {char_count} ตัว\n"
        summary += f"🔤 **จำนวนบรรทัด:** {line_count} บรรทัด"
        
        return summary
        
    except Exception as e:
        logger.error(f"Error formatting summary: {str(e)}")
        return f"❌ เกิดข้อผิดพลาดในการจัดรูปแบบ: {str(e)}"

def extract_qr_code(image_path: str) -> Optional[str]:
    """
    แยก QR Code จากรูปภาพ (EasyOCR ไม่รองรับ QR Code โดยตรง)
    ใช้สำหรับอนาคต หรือเพิ่มเติมด้วย library อื่น
    
    Args:
        image_path (str): path ของไฟล์รูปภาพ
        
    Returns:
        Optional[str]: ข้อมูลใน QR Code หรือ None
    """
    try:
        # TODO: เพิ่มการอ่าน QR Code ด้วย pyzbar หรือ library อื่น
        logger.info("QR Code extraction ยังไม่รองรับ")
        return None
        
    except Exception as e:
        logger.error(f"Error extracting QR code: {str(e)}")
        return None