# B2B портал для Инфо-Предприятия — этап 3

Эта версия добавляет к этапу 2:

- фоновые циклы синхронизации по профилям интеграции;
- центр мониторинга интеграции и логи обмена;
- импорт статусов заказов из ERP (CSV/XML);
- историю статусов по каждому заказу;
- email-уведомления о новых заказах, смене статуса и ошибках синхронизации;
- полноценные миграции, чтобы проект поднимался с нуля.

## Быстрый старт

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

Откройте:

- `/` — каталог
- `/dashboard/` — кабинет клиента
- `/orders/` — заказы и история статусов
- `/integrations/` — центр интеграции (только staff)

## Настройка email

По умолчанию используется console backend. Для SMTP задайте переменные в `.env`:

```env
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=smtp.example.com
EMAIL_PORT=587
EMAIL_HOST_USER=user@example.com
EMAIL_HOST_PASSWORD=secret
EMAIL_USE_TLS=1
DEFAULT_FROM_EMAIL=noreply@example.com
MANAGER_NOTIFICATION_EMAILS=ops@example.com,sales@example.com
```

## Профиль интеграции

В админке создайте `Профиль интеграции` и заполните пути:

- `import_xml_path`
- `offers_xml_path`
- `images_dir_path`
- `export_orders_path`
- `status_feed_path`

`status_feed_path` может указывать на CSV вида:

```csv
site_number,external_number,status,comment
WEB202601010101010000,ERP-10001,processing,Заказ принят
WEB202601010101010000,ERP-10001,invoiced,Счет выставлен
WEB202601010101010000,ERP-10001,shipped,Отгружено
```

Поддерживаемые статусы:

- `new`
- `processing`
- `approved`
- `exported`
- `invoiced`
- `shipped`
- `completed`
- `cancelled`

## Команды

### Импорт каталога и предложений

```bash
python manage.py import_commerceml --import-xml path/to/import.xml --offers-xml path/to/offers.xml --images-dir path/to/import_files
```

### Экспорт заказов

```bash
python manage.py export_orders_commerceml --output path/to/orders.xml
```

### Импорт статусов заказов

```bash
python manage.py import_order_statuses --file path/to/status_feed.csv
```

### Полный цикл по профилю

```bash
python manage.py run_sync_profile --code default
```

### Циклический фоновый запуск

```bash
python manage.py run_sync_profile --code default --loop
```

Или с явным интервалом в секундах:

```bash
python manage.py run_sync_profile --code default --loop --interval 300
```

## Что уже покрыто этапом 3

- профили интеграции с расписанием и путями;
- синхронизация каталогов, цен, остатков и заказов;
- импорт ERP-статусов в историю заказа;
- уведомления при создании заказа и при смене статуса;
- служебные логи для импорта, экспорта, системных ошибок и статусов.

## Что логично делать дальше

- реальный двусторонний протокол подтверждения получения `orders.xml`;
- парсинг статусов из боевого CommerceML-документа ERP, если он отличается от простого XML/CSV;
- асинхронные задачи через Celery/RQ вместо циклической management command;
- фронтенд на отдельном SPA, если понадобится тяжелый UX.
