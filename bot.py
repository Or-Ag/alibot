import os
import requests
import hashlib
import time
import random
import asyncio
from telegram import Bot

# ---------- AliExpress ----------
ALI_APP_KEY = "518388"  # לא סודי
ALI_APP_SECRET = os.getenv("ALI_APP_SECRET")
ALI_TRACKING_ID = os.getenv("ALI_TRACKING_ID")

# ---------- Telegram ----------
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = int(os.getenv("CHAT_ID"))  # חובה INT

# ---------- AI ----------
OPENAI

]

# ---------- AliExpress helpers ----------

def ali_sign(params, secret):
    items = sorted(params.items())
    base = secret + "".join(f"{k}{v}" for k, v in items) + secret
    return hashlib.md5(base.encode("utf8")).hexdigest().upper()

def ali_request(method, extra_params):
    base_url = "https://api-sg.aliexpress.com/sync"

    params = {
        "app_key": ALI_APP_KEY,
        "timestamp": int(time.time() * 1000),
        "format": "json",
        "sign_method": "md5",
        "v": "1.0",
        "method": method,
    }

    params.update(extra_params)
    params["sign"] = ali_sign(params, ALI_APP_SECRET)

    res = requests.get(base_url, params=params)
    print("סטטוס מהשרת:", res.status_code)

    try:
        data = res.json()
        print("מפתחות למעלה:", list(data.keys()))
        return data
    except Exception as e:
        print("שגיאה בקריאת JSON:", e)
        print("טקסט גולמי:", res.text[:500])
        return {}

def get_random_product():
    keyword = random.choice(KEYWORDS)
    print("מחפש מוצר עבור:", keyword)

    data = ali_request("aliexpress.affiliate.product.query", {
        "keywords": keyword,
        "page_no": 1,
        "page_size": 10,
        "tracking_id": ALI_TRACKING_ID,
    })

    print("תשובה מלאה ל-product.query:", str(data)[:500])

    try:
        root = data["aliexpress_affiliate_product_query_response"]
        resp_result = root.get("resp_result", {})
        result = resp_result.get("result", {})
        products_obj = result.get("products", {})
        products = products_obj.get("product", [])
        if not products:
            print("אין מוצרים ב-resp_result")
            return None

        product = random.choice(products)
    except Exception as e:
        print("לא הצלחתי להוציא מוצר:", e)
        return None

    # שדות נפוצים לפי מה שראינו ב-testali
    title = product.get("product_title", "")
    if not title:
        title = product.get("product_name", "")

    image = product.get("product_main_image_url")
    if not image:
        small_images = product.get("product_small_image_urls", {}).get("string", [])
        image = small_images[0] if small_images else None

    price = product.get("target_sale_price") or product.get("app_sale_price") or product.get("original_price", "")
    url = product.get("product_detail_url")

    if not url:
        print("אין product_detail_url במוצר")
        return None

    return {
        "title": title,
        "image": image,
        "price": price,
        "url": url,
    }

def convert_to_affiliate_link(url):
    data = ali_request("aliexpress.affiliate.link.generate", {
        "source_value": url,
        "tracking_id": ALI_TRACKING_ID,
    })

    print("תשובה ל-link.generate:", str(data)[:500])

    try:
        root = next(v for k, v in data.items() if k.endswith("_response"))
        resp_result = root.get("resp_result", {})
        url_list = resp_result.get("promotion_url_list", [])
        if not url_list:
            print("אין promotion_url_list, מחזיר לינק רגיל")
            return url
        return url_list[0].get("promotion_url", url)
    except Exception as e:
        print("לא הצלחתי להוציא לינק אפילייט:", e)
        return url

def build_caption(p, link):
    return f"""🔧 {p['title']}

💰 מחיר: {p['price']}

🔗 לרכישה:
{link}
"""

# ---------- טלגרם לופ ----------

async def start_bot():
    bot = Bot(TELEGRAM_TOKEN)

    while True:
        try:
            product = get_random_product()
            if product is None:
                print("לא נמצא מוצר - שולח הודעת טסט בלבד")
                await bot.send_message(
                    chat_id=CHAT_ID,
                    text="לא נמצא מוצר מתאים מאליאקספרס אבל הבוט חי ✅"
                )
            else:
                aff_link = convert_to_affiliate_link(product["url"])
                caption = build_caption(product, aff_link)

                if product["image"]:
                    await bot.send_photo(
                        chat_id=CHAT_ID,
                        photo=product["image"],
                        caption=caption
                    )
                else:
                    await bot.send_message(
                        chat_id=CHAT_ID,
                        text=caption
                    )

                print("נשלח מוצר לטלגרם")

        except Exception as e:
            print("שגיאה כללית בלופ:", e)

        # בזמן בדיקות - 15 שניות. אחר כך תעלה לשעה.
        await asyncio.sleep(15)

if __name__ == "__main__":
    asyncio.run(start_bot())


