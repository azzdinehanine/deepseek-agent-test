# DeepSeek Agent — وكيل ذكاء اصطناعي على Google Cloud Run

وكيل محادثة مع أدوات (استدعاء دوال تلقائي) مبني على **Vertex AI / Gemini**،
جاهز للنشر على Cloud Run بدون Docker محلي.

## ما يفعله

- `POST /chat` — يرسل رسالة للوكيل ويستقبل الرد
- أدوات حقيقية: `get_weather` (طقس تجريبي) و`add_numbers` (جمع)
- `GET /` — واجهة وِب بسيطة للتجربة الفورية في المتصفح
- `GET /health` — فحص صحة للاستخدام مع Cloud Run والمراقبة
  (المسار `/healthz` محجوز في طبقة Google أمام Cloud Run ويرجع 404 — لا تستخدمه)

**لا يحتاج مفتاح API**: يستخدم حساب خدمة Cloud Run للمصادقة على Vertex AI.

## الملفات

| الملف | الدور |
|---|---|
| `main.py` | تطبيق Flask + الوكيل + الأدوات + واجهة HTML |
| `requirements.txt` | الاعتماديات (flask, gunicorn, google-genai) |
| `Dockerfile` | صورة Python 3.12 صريحة (بديل موصى به عن buildpacks) |
| `.python-version` | يمنع اختيار Python 3.14 تلقائيًا (سبب فشل سابق) |
| `.gcloudignore` | يمنع رفع ملفات غير لازمة أو أسرار |

## النشر

```bash
# 1) المشروع والمنطقة
export PROJECT_ID=project-f8643781-f075-4886-a4e
export REGION=us-central1
gcloud config set project "$PROJECT_ID"

# 2) صلاحية الوكيل لاستدعاء Vertex AI
gcloud projects add-iam-policy-binding "$PROJECT_ID" \
  --member="serviceAccount:948681570348-compute@developer.gserviceaccount.com" \
  --role="roles/aiplatform.user"

# 3) النشر من جذر هذا المجلد (لا من ~)
cd ~/deepseek-agent-test
gcloud run deploy agent-service \
  --source . \
  --region "$REGION" \
  --allow-unauthenticated \
  --memory 1Gi \
  --cpu 1 \
  --timeout 300 \
  --concurrency 40 \
  --max-instances 3 \
  --set-env-vars "GOOGLE_CLOUD_PROJECT=$PROJECT_ID,GOOGLE_CLOUD_REGION=$REGION"
```

## التحقق

```bash
URL=$(gcloud run services describe agent-service --region us-central1 --format='value(status.url)')
curl -s "$URL/health"           # {"ok":true,...}
curl -s -X POST "$URL/chat" -H 'content-type: application/json' \
     -d '{"message":"ما هو الطقس في الجزائر؟"}' | head -c 400
open "$URL"                      # أو افتح الرابط في المتصفح
```

## متغيّرات البيئة

| المتغير | الافتراضي | الوصف |
|---|---|---|
| `GOOGLE_CLOUD_PROJECT` | — (إلزامي) | معرّف المشروع |
| `GOOGLE_CLOUD_REGION` | `us-central1` | منطقة Vertex AI |
| `MODEL_ID` | `gemini-2.5-flash` | النموذج المستخدم |
| `PORT` | `8080` | يضبطه Cloud Run تلقائيًا |

## ملاحظات

- لاستخدام DeepSeek API بدل Gemini: خزّن المفتاح في Secret Manager واقرأه بـ
  `os.environ["DEEPSEEK_API_KEY"]`، وبدّل مُنشئ العميل في `main.py` (البنية نفسها).
- اختبر محليًا قبل النشر: `pip install -r requirements.txt && python main.py`
- بعد نجاح النشر ثبّت الإصدارات الفعلية: `pip freeze > requirements.txt`
