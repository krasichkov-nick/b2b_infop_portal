# Чеклист разработчика по файлам

## 1. Стабильные идентификаторы
- `apps/customers/models.py`: добавить/поддержать `external_id`, автозаполнение `company-{id}`.
- `apps/orders/models.py`: добавить `external_uid`, `erp_export_state`, `exported_at`, `locked_after_export`, `last_export_hash`, ссылки на batch/artifact.
- `apps/customers/admin.py`, `apps/orders/admin.py`: показать новые поля в админке.

## 2. Пакеты обмена и артефакты
- `apps/integrations/models.py`: добавить `ExchangeBatch`, `ExchangeArtifact`, `ERPStatusMapping`, связать `ExchangeLog` с batch.
- `apps/integrations/admin.py`: зарегистрировать новые модели.

## 3. Валидация заказа перед ERP
- `apps/integrations/services/order_validation.py`: новый сервис `validate_order_for_export`.
- `apps/orders/services.py`: при создании заказа переводить в `validated`, дописать ERP-поля в события.

## 4. Экспорт orders.xml
- `apps/integrations/services/order_export.py`:
  - экспорт только `new/validated` по умолчанию;
  - `Документ/Ид = external_uid`;
  - `Контрагент/Ид = company.external_id`;
  - без контейнера `Документы`;
  - создавать batch + artifact + checksum;
  - блокировать заказ после выгрузки.
- `apps/integrations/management/commands/export_orders_commerceml.py`: добавить `--force`, `--order-ids`, `--batch-comment`.
- `apps/integrations/management/commands/validate_orders_for_export.py`: новый check-командлет.
- `apps/integrations/management/commands/show_exchange_batch.py`: новый просмотр пакета.

## 5. Импорт статусов ERP
- `apps/integrations/services/status_import.py`: искать заказ по `external_uid`, сохранять artifact, применять только последнее состояние по заказу.
- `apps/integrations/management/commands/import_order_statuses.py`: расширить вывод.
- `apps/integrations/management/commands/reconcile_orders.py`: новый командлет диагностики.

## 6. Эксплуатационные страницы
- `apps/integrations/views.py`: список пакетов, детали, ручной экспорт, ручной импорт статусов, дашборд.
- `apps/integrations/urls.py`: новые маршруты.
- `config/urls.py`: подключить `integrations/`.
- `templates/integrations/*.html`: новые шаблоны.
- `templates/portal/order_detail.html`: показать ERP-поля заказа.

## 7. Боевой прогон после замены файлов
1. `python manage.py makemigrations`
2. `python manage.py migrate`
3. `python manage.py validate_orders_for_export`
4. `python manage.py export_orders_commerceml --output ... --profile-code ...`
5. проверить `admin` -> ExchangeBatch / ExchangeArtifact
6. загрузить `orders.xml` в Инфо-Предприятие
7. импортировать файл статусов командой `import_order_statuses`
