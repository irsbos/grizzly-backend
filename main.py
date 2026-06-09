# main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import requests
import config

app = FastAPI(title="Grizzly SMS API Bridge")

# تفعيل الـ CORS لتمكين واجهة الـ Mini App من الاتصال بالسيرفر دون قيود حماية المتصفح
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

GRIZZLY_URL = "https://api.grizzlysms.com/stubs/handler_api.php"

@app.get("/api/prices")
def get_prices():
    """ جلب الأسعار الحية من Grizzly وإضافة هامش الربح الخاص بك """
    try:
        import os
        # 🎯 تعديل ذكي: القراءة من السيرفر مباشرة لقطع الشك باليقين
        api_key = os.environ.get("GRIZZLY_API_KEY")
        
        # فحص إذا كان المفتاح فارغاً أو يحتوي على النص الافتراضي القديم
        if not api_key or api_key == "YOUR_GRIZZLY_API_KEY" or api_key.strip() == "":
            return {
                "status": "error", 
                "message": "🚨 السيرفر لم يجد المفتاح في إعدادات Render! تأكد من كتابة الاسم بدقة GRIZZLY_API_KEY وضغط Save Changes"
            }

        params = {
            "api_key": api_key, # استخدام المفتاح المأخوذ مباشرة من السيرفر
            "action": "getPrices"
        }
        response = requests.get(GRIZZLY_URL, params=params)
        if response.status_code != 200:
            return {"status": "error", "message": f"المزود لا يستجيب، رمز الحالة: {response.status_code}"}
        
        try:
            raw_data = response.json()
        except Exception:
            return {"status": "error", "message": f"Grizzly returned non-JSON text: {response.text[:300]}"}
            
        formatted_list = []
        for country_id, services in raw_data.items():
            for service_code, details in services.items():
                cost = float(details.get("cost", 0))
                count = int(details.get("count", 0))
                if count > 0:
                    final_price = round(cost * config.PROFIT_MARGIN, 2)
                    formatted_list.append({
                        "country": country_id,
                        "service": service_code,
                        "price": final_price,
                        "available": count
                    })
        return {"status": "success", "data": formatted_list}
    except Exception as e:
        return {"status": "error", "message": f"Server Exception: {str(e)}"}
