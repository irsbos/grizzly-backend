import requests
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware  # 1. استدعاء أداة السماح بالاتصال
import config

app = FastAPI()

# 2. تفعيل الصلاحيات لكي يوافق السيرفر على إرسال الأسعار للتطبيق المصغر
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # يسمح للتطبيق بالوصول للبيانات بدون حظر
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 3. رابط موقع Grizzly الأساسي
GRIZZLY_URL = "https://api.grizzlysms.com/stubs/handler_api.php"

# 4. دالة جلب الأسعار وحساب الأرباح التي نجحت معنا
@app.get("/api/prices")
def get_prices():
    """ جلب الأسعار الحية من Grizzly وإضافة هامش الربح الخاص بك """
    try:
        import os
        # القراءة من سيرفر Render مباشرة
        api_key = os.environ.get("GRIZZLY_API_KEY")
        
        # فحص إذا كان المفتاح فارغاً
        if not api_key or api_key == "YOUR_GRIZZLY_API_KEY" or api_key.strip() == "":
            return {
                "status": "error", 
                "message": "🚨 السيرفر لم يجد المفتاح في إعدادات Render!"
            }

        params = {
            "api_key": api_key,
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
