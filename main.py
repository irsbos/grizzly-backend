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
        params = {
            "api_key": config.GRIZZLY_API_KEY,
            "action": "getPrices"
        }
        response = requests.get(GRIZZLY_URL, params=params)
        if response.status_code != 200:
            return {"status": "error", "message": "المزود لا يستجيب حالياً"}
        
        raw_data = response.json()
        formatted_list = []
        
        # تنسيق البيانات وهيكلتها: { country_id: { service_code: { cost: X, count: Y } } }
        for country_id, services in raw_data.items():
            for service_code, details in services.items():
                cost = float(details.get("cost", 0))
                count = int(details.get("count", 0))
                
                if count > 0:  # عرض الخدمات التي تحتوي على أرقام متوفرة فقط
                    final_price = round(cost * config.PROFIT_MARGIN, 2)
                    formatted_list.append({
                        "country": country_id,
                        "service": service_code,
                        "price": final_price,
                        "available": count
                    })
        return {"status": "success", "data": formatted_list}
    except Exception as e:
        return {"status": "error", "message": str(e)}
