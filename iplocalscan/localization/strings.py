from __future__ import annotations

TRANSLATIONS = {
    "en": {
        "app.title": "IP Local Scan",
        "main.network_range_label": "Network range",
        "main.network_range_placeholder": "Example: 192.168.1.0/24",
        "main.scan_button": "Scan",
        "main.stop_button": "Stop",
        "main.history_button": "History",
        "main.filter_label": "Filter",
        "main.filter_placeholder": (
            "Search by IP, MAC, vendor, hostname, ports, or services"
        ),
        "main.online_only_checkbox": "Online only",
        "main.has_open_ports_checkbox": "Has open ports",
        "main.has_services_checkbox": "Has services",
        "history.title": "Recent Scans",
        "history.description": "The latest {limit} stored scans are listed below.",
        "history.empty": "No scan history is available yet.",
        "history.saved_scans_label": "Saved scans",
        "history.preview_label": "Results preview",
        "history.scan_item": (
            "{started_at} | {network_range} | {status} | {result_count} result(s)"
        ),
        "history.details.empty": "Select a saved scan to preview its results.",
        "history.close_button": "Close",
        "table.ip_address": "IP Address",
        "table.mac_address": "MAC Address",
        "table.vendor": "Vendor",
        "table.hostname": "Hostname",
        "table.status": "Status",
        "table.change_status": "Change Status",
        "table.open_ports": "Open Ports",
        "table.services": "Services",
        "status.ready": "Ready.",
        "status.invalid_network": (
            "Enter an IPv4 network in CIDR format, for example {example}."
        ),
        "status.scan_started": "Starting scan for {network_range}...",
        "status.scan_progress.discovery": (
            "Discovering hosts in {network_range}: checked {completed_hosts}/{total_hosts}, "
            "found {discovered_hosts} online."
        ),
        "status.scan_progress.ports": (
            "Scanning ports for {total_hosts} host(s): completed {completed_hosts}/{total_hosts}, "
            "{hosts_with_open_ports} host(s) with open ports."
        ),
        "status.scan_completed": (
            "Scan completed for {network_range}. Found {result_count} online host(s) and finished basic port scanning."
        ),
        "status.scan_stopped": (
            "Scan stopped for {network_range}. Found {result_count} online host(s) before cancellation."
        ),
        "status.scan_failed": "Scan failed: {reason}",
        "status.scan_already_running": "A scan is already in progress.",
        "status.no_active_scan": "There is no active scan to stop.",
        "status.stop_requested": "Stopping scan...",
        "status.host.unknown": "Unknown",
        "status.host.up": "Online",
        "status.host.down": "Offline",
        "status.change.new": "New",
        "status.change.changed": "Changed",
        "status.change.unchanged": "Unchanged",
        "status.change.removed": "Missing",
        "status.scan.pending": "Pending",
        "status.scan.running": "Running",
        "status.scan.completed": "Completed",
        "status.scan.stopped": "Stopped",
        "status.scan.failed": "Failed",
        "progress.stage.ready": "Ready to scan.",
        "progress.stage.discovery": "Discovering hosts...",
        "progress.stage.port_scan": "Scanning ports...",
        "progress.stage.finalizing": "Finalizing results...",
        "progress.stage.completed": "Scan completed.",
        "progress.stage.stopped": "Scan stopped.",
        "progress.stage.failed": "Scan failed.",
        "progress.detail.ready": "Enter a CIDR range to start a scan.",
        "progress.detail.starting": "Preparing scan for {network_range}...",
        "progress.detail.discovery": (
            "{completed_hosts}/{total_hosts} IPs checked, {discovered_hosts} host(s) found."
        ),
        "progress.detail.ports": (
            "{completed_hosts}/{total_hosts} host(s) scanned for ports, "
            "{hosts_with_open_ports} with open ports."
        ),
        "progress.detail.finalizing": (
            "Comparing with the previous scan and saving results..."
        ),
        "progress.detail.completed": (
            "{result_count} host(s) available in the final results."
        ),
        "progress.detail.stopped": (
            "{result_count} host(s) collected before cancellation."
        ),
        "progress.detail.failed": "The scan ended with an error: {reason}",
        "scan.note.completed": "Host discovery and basic port scanning completed.",
        "scan.note.stop_requested": "The scan was stopped by the user.",
        "common.not_available": "N/A",
    },
    "ru": {
        "app.title": "IP Local Scan",
        "main.network_range_label": "Диапазон сети",
        "main.network_range_placeholder": "Пример: 192.168.1.0/24",
        "main.scan_button": "Сканировать",
        "main.stop_button": "Стоп",
        "main.history_button": "История",
        "main.filter_label": "Фильтр",
        "main.filter_placeholder": (
            "Поиск по IP, MAC, производителю, имени хоста, портам или сервисам"
        ),
        "main.online_only_checkbox": "Только онлайн",
        "main.has_open_ports_checkbox": "Есть открытые порты",
        "main.has_services_checkbox": "Есть сервисы",
        "history.title": "Последние сканирования",
        "history.description": "Ниже показаны последние {limit} сохраненных сканирования.",
        "history.empty": "История сканирований пока пуста.",
        "history.saved_scans_label": "Сохраненные сканирования",
        "history.preview_label": "Предпросмотр результатов",
        "history.scan_item": (
            "{started_at} | {network_range} | {status} | {result_count} результат(ов)"
        ),
        "history.details.empty": "Выберите сохраненное сканирование для просмотра результатов.",
        "history.close_button": "Закрыть",
        "table.ip_address": "IP-адрес",
        "table.mac_address": "MAC-адрес",
        "table.vendor": "Производитель",
        "table.hostname": "Имя хоста",
        "table.status": "Статус",
        "table.change_status": "Изменение",
        "table.open_ports": "Открытые порты",
        "table.services": "Сервисы",
        "status.ready": "Готово.",
        "status.invalid_network": (
            "Введите IPv4-сеть в формате CIDR, например {example}."
        ),
        "status.scan_started": "Запуск сканирования для {network_range}...",
        "status.scan_progress.discovery": (
            "Поиск хостов в {network_range}: проверено {completed_hosts}/{total_hosts}, "
            "найдено в сети {discovered_hosts}."
        ),
        "status.scan_progress.ports": (
            "Сканирование портов для {total_hosts} хостов: завершено {completed_hosts}/{total_hosts}, "
            "хостов с открытыми портами: {hosts_with_open_ports}."
        ),
        "status.scan_completed": (
            "Сканирование {network_range} завершено. Найдено {result_count} узлов в сети, базовое сканирование портов завершено."
        ),
        "status.scan_stopped": (
            "Сканирование {network_range} остановлено. До отмены найдено {result_count} узлов в сети."
        ),
        "status.scan_failed": "Ошибка сканирования: {reason}",
        "status.scan_already_running": "Сканирование уже выполняется.",
        "status.no_active_scan": "Нет активного сканирования для остановки.",
        "status.stop_requested": "Остановка сканирования...",
        "status.host.unknown": "Неизвестно",
        "status.host.up": "В сети",
        "status.host.down": "Не в сети",
        "status.change.new": "Новый",
        "status.change.changed": "Изменен",
        "status.change.unchanged": "Без изменений",
        "status.change.removed": "Пропал",
        "status.scan.pending": "Ожидание",
        "status.scan.running": "Выполняется",
        "status.scan.completed": "Завершено",
        "status.scan.stopped": "Остановлено",
        "status.scan.failed": "Ошибка",
        "progress.stage.ready": "Готово к сканированию.",
        "progress.stage.discovery": "Поиск хостов...",
        "progress.stage.port_scan": "Сканирование портов...",
        "progress.stage.finalizing": "Подготовка результатов...",
        "progress.stage.completed": "Сканирование завершено.",
        "progress.stage.stopped": "Сканирование остановлено.",
        "progress.stage.failed": "Сканирование завершилось с ошибкой.",
        "progress.detail.ready": "Введите диапазон CIDR, чтобы начать сканирование.",
        "progress.detail.starting": "Подготовка сканирования для {network_range}...",
        "progress.detail.discovery": (
            "Проверено IP: {completed_hosts}/{total_hosts}, найдено хостов: {discovered_hosts}."
        ),
        "progress.detail.ports": (
            "Хостов проверено по портам: {completed_hosts}/{total_hosts}, "
            "с открытыми портами: {hosts_with_open_ports}."
        ),
        "progress.detail.finalizing": (
            "Сравниваем с предыдущим сканированием и сохраняем результаты..."
        ),
        "progress.detail.completed": (
            "В итоговых результатах доступно {result_count} хост(ов)."
        ),
        "progress.detail.stopped": (
            "До отмены собрано {result_count} хост(ов)."
        ),
        "progress.detail.failed": "Сканирование завершилось с ошибкой: {reason}",
        "scan.note.completed": "Обнаружение хостов и базовое сканирование портов завершены.",
        "scan.note.stop_requested": "Сканирование остановлено пользователем.",
        "common.not_available": "Н/Д",
    },
}
