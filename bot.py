# bot.py
import telebot
from telebot import types
import requests
import json
import config
import database

bot = telebot.TeleBot(config.BOT_TOKEN)
database.init_db()  # تشغيل وتجهيز قاعدة البيانات تلقائياً

GRIZZLY_URL = "https://api.grizzly-sms.com/stubs/handler_api.php"

@bot.message_handler(commands=['start'])
def send_welcome(message):
    user_id = message.from_user.id
    username = message.from_user.username or "مستخدم"
    balance = database.get_user_balance(user_id, username)
    
    markup = types.InlineKeyboardMarkup()
    # ربط كود زر فتح متجر الـ Mini App مباشرة بالرابط الخاص بك
    webapp_info = types.WebAppInfo(url=config.WEBAPP_URL)
    btn_store = types.InlineKeyboardButton("🛒 فتح متجر الأرقام", web_app=webapp_info)
    btn_balance = types.InlineKeyboardButton("💰 رصيدي ومحفظتي", callback_data="check_balance")
    markup.add(btn_store)
    markup.add(btn_balance)
    
    msg_text = (
        f"👋 أهلاً بك يا {username} في بوت تفعيل الأرقام التلقائي!\n\n"
        f"💵 رصيدك الحالي: {balance} نقطة.\n\n"
        f"اضغط على الزر أدناه لفتح واجهة المتجر واختيار رقمك الحصري المباشر."
    )
    bot.send_message(message.chat.id, msg_text, reply_markup=markup, parse_mode="Markdown")

@bot.callback_query_handler(func=lambda call: call.data == "check_balance")
def check_balance_callback(call):
    balance = database.get_user_balance(call.from_user.id)
    bot.answer_callback_query(call.id, f"رصيدك الحالي هو: {balance} نقطة")

# استقبال ومعالجة البيانات المرسلة فوراً من واجهة الـ Mini App عند الضغط على طلب الرقم
@bot.message_handler(content_types=['web_app_data'])
def handle_webapp_data(message):
    user_id = message.from_user.id
    chat_id = message.chat.id
    
    try:
        data = json.loads(message.web_app_data.data)
        service = data.get("service")
        country = data.get("country")
        price = float(data.get("price", 0))
        
        # 1. التحقق من رصيد المستخدم أولاً في البوت
        user_balance = database.get_user_balance(user_id)
        if user_balance < price:
            bot.send_message(chat_id, "❌ عذراً! رصيدك غير كافٍ لشراء هذا الرقم. يرجى شحن محفظتك أولاً.")
            return
            
        bot.send_message(chat_id, f"⏳ جاري طلب رقم {service.upper()} لدولة ({country})... يرجى الانتظار ثواني.")
        
        # 2. إرسال أمر الشراء الفعلي لـ Grizzly SMS عبر الـ API
        params = {
            "api_key": config.GRIZZLY_API_KEY,
            "action": "getNumber",
            "service": service,
            "country": country
        }
        res = requests.get(GRIZZLY_URL, params=params)
        res_text = res.text
        
        # في حال نجاح العملية تكون الاستجابة بصيغة: ACCESS_NUMBER:$id:$number
        if res_text.startswith("ACCESS_NUMBER"):
            _, grizzly_id, phone_number = res_text.split(":")
            
            # خصم الرصيد مؤقتاً من محفظة البوت
            database.update_user_balance(user_id, -price)
            
            # إرسال بيانات الرقم وعرض أزرار التحكم بالفحص والإلغاء تحتها
            markup = types.InlineKeyboardMarkup()
            btn_check = types.InlineKeyboardButton("🔄 فحص وصول الكود", callback_data=f"check_{grizzly_id}_{price}")
            btn_cancel = types.InlineKeyboardButton("❌ إلغاء واسترجاع النقاط", callback_data=f"cancel_{grizzly_id}_{price}")
            markup.add(btn_check, btn_cancel)
            
            success_msg = (
                f"✅ تم استخراج الرقم بنجاح!\n\n"
                f"📱 الرقم: `+{phone_number}`\n"
                f"🛠️ الخدمة: {service.upper()}\n"
                f"💵 التكلفة: {price} نقطة\n\n"
                f"استخدم الرقم الآن في التطبيق المستهدف، واضغط على زر الفحص بالأسفل لجلب كود التفعيل فوراً."
            )
            bot.send_message(chat_id, success_msg, reply_markup=markup, parse_mode="Markdown")
        else:
            bot.send_message(chat_id, f"❌ خطأ من مزود الخدمة، أو أن الرقم غير متوفر حالياً. التفاصيل: {res_text}")
            
    except Exception as e:
        bot.send_message(chat_id, f"❌ حدث خطأ أثناء معالجة الطلب: {str(e)}")

@bot.callback_query_handler(func=lambda call: call.data.startswith("check_") or call.data.startswith("cancel_"))
def handle_order_actions(call):
    action, grizzly_id, price = call.data.split("_")
    price = float(price)
    user_id = call.from_user.id
    chat_id = call.message.chat.id
    
    if action == "check":
        # طلب حالة الكود الحالية من السيرفر
        params = {
            "api_key": config.GRIZZLY_API_KEY,
            "action": "getStatus",
            "id": grizzly_id
        }
        res = requests.get(GRIZZLY_URL, params=params)
        res_text = res.text
        
        if res_text.startswith("STATUS_OK"):
            code = res_text.split(":")[1]
            bot.send_message(chat_id, f"🎉 مبروك! وصل كود التفعيل الخاص بك بنجاح:\n\n🔑 الكود: `{code}`", parse_mode="Markdown")
            # إرسال إشعار للموقع لإتمام تفعيل الرقم (حالة رقم 6 تعني اكتمال التفعيل)
            requests.get(GRIZZLY_URL, params={"api_key": config.GRIZZLY_API_KEY, "action": "setStatus", "id": grizzly_id, "status": "6"})
            # إخفاء أزرار التحكم السابقة لعدم الضغط عليها مجدداً
            bot.edit_message_reply_markup(chat_id, call.message.message_id, reply_markup=None)
        elif "STATUS_WAIT_CODE" in res_text:
            bot.answer_callback_query(call.id, "⏳ الكود لم يصل بعد.. يرجى الاستمرار في الانتظار وإعادة المحاولة.", show_alert=True)
        else:
            bot.send_message(chat_id, f"ℹ️ حالة الرقم الحالية من المصدر: {res_text}")
            
    elif action == "cancel":
        # إلغاء الطلب في موقع Grizzly (حالة رقم 8 تعني إلغاء الطلب)
        params = {
            "api_key": config.GRIZZLY_API_KEY,
            "action": "setStatus",
            "id": grizzly_id,
            "status": "8"
        }
        requests.get(GRIZZLY_URL, params=params)
        
        # إعادة النقاط بالكامل لمحفظة العميل التابع للبوت لعدم وصول كود
        database.update_user_balance(user_id, price)
        bot.send_message(chat_id, f"↩️ تم إلغاء طلب الرقم بنجاح، وإعادة {price} نقطة إلى محفظتك بالكامل.")
        bot.edit_message_reply_markup(chat_id, call.message.message_id, reply_markup=None)

if __name__ == '__main__':
    print("البوت يعمل الآن ويستمع للأوامر بنجاح...")
    bot.infinity_polling()