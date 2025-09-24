"""
Простой веб-сервер для отображения пользовательского соглашения
"""

from flask import Flask, render_template_string
import os

app = Flask(__name__)

AGREEMENT_TEMPLATE = """
<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Пользовательское соглашение - AirCloud VPN</title>
    <style>
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            line-height: 1.6;
            color: #333;
            max-width: 800px;
            margin: 0 auto;
            padding: 20px;
            background: #f5f5f5;
        }
        .container {
            background: white;
            padding: 30px;
            border-radius: 10px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }
        h1 {
            color: #2c3e50;
            text-align: center;
            border-bottom: 3px solid #3498db;
            padding-bottom: 10px;
        }
        h2 {
            color: #34495e;
            margin-top: 30px;
        }
        .highlight {
            background: #e8f4fd;
            padding: 15px;
            border-left: 4px solid #3498db;
            margin: 20px 0;
        }
        .footer {
            text-align: center;
            margin-top: 40px;
            padding-top: 20px;
            border-top: 1px solid #eee;
            color: #666;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>ПОЛЬЗОВАТЕЛЬСКОЕ СОГЛАШЕНИЕ<br>VPN-сервиса AirCloud</h1>
        
        <div class="highlight">
            <strong>Внимание!</strong> Используя наш сервис, вы автоматически соглашаетесь с условиями данного соглашения.
        </div>

        <h2>1. ОБЩИЕ ПОЛОЖЕНИЯ</h2>
        <p><strong>1.1.</strong> Настоящее Пользовательское соглашение (далее — «Соглашение») регулирует отношения между администрацией VPN-сервиса AirCloud (далее — «Сервис») и пользователем при использовании услуг VPN.</p>
        <p><strong>1.2.</strong> Используя Сервис, пользователь соглашается с условиями настоящего Соглашения в полном объеме.</p>

        <h2>2. ОПИСАНИЕ УСЛУГ</h2>
        <p><strong>2.1.</strong> Сервис предоставляет услуги виртуальной частной сети (VPN) для обеспечения безопасного и анонимного доступа в интернет.</p>
        <p><strong>2.2.</strong> Услуги предоставляются на платной основе согласно выбранному тарифному плану.</p>

        <h2>3. ПРАВА И ОБЯЗАННОСТИ ПОЛЬЗОВАТЕЛЯ</h2>
        <p><strong>3.1.</strong> Пользователь обязуется:</p>
        <ul>
            <li>Использовать Сервис исключительно в законных целях</li>
            <li>Не нарушать права третьих лиц</li>
            <li>Не использовать Сервис для незаконной деятельности</li>
            <li>Соблюдать законодательство своей страны</li>
        </ul>
        
        <p><strong>3.2.</strong> Пользователь имеет право:</p>
        <ul>
            <li>Получать качественные услуги VPN</li>
            <li>Обращаться в техническую поддержку</li>
            <li>Расторгнуть соглашение в любое время</li>
        </ul>

        <h2>4. ПРАВА И ОБЯЗАННОСТИ АДМИНИСТРАЦИИ</h2>
        <p><strong>4.1.</strong> Администрация обязуется:</p>
        <ul>
            <li>Предоставлять услуги VPN надлежащего качества</li>
            <li>Обеспечивать конфиденциальность данных пользователя</li>
            <li>Предоставлять техническую поддержку</li>
        </ul>
        
        <p><strong>4.2.</strong> Администрация имеет право:</p>
        <ul>
            <li>Изменять условия Соглашения с уведомлением пользователей</li>
            <li>Приостанавливать или прекращать предоставление услуг при нарушении условий</li>
        </ul>

        <h2>5. ОПЛАТА И ВОЗВРАТ СРЕДСТВ</h2>
        <p><strong>5.1.</strong> Оплата производится согласно выбранному тарифному плану.</p>
        <p><strong>5.2.</strong> Возврат средств возможен в течение 24 часов с момента оплаты при технических проблемах со стороны Сервиса.</p>

        <h2>6. КОНФИДЕНЦИАЛЬНОСТЬ</h2>
        <div class="highlight">
            <p><strong>6.1.</strong> Администрация не ведет логи активности пользователей.</p>
            <p><strong>6.2.</strong> Персональные данные пользователей защищены и не передаются третьим лицам.</p>
        </div>

        <h2>7. ОТВЕТСТВЕННОСТЬ</h2>
        <p><strong>7.1.</strong> Администрация не несет ответственности за действия пользователя в сети интернет.</p>
        <p><strong>7.2.</strong> Пользователь несет полную ответственность за соблюдение законодательства при использовании Сервиса.</p>

        <h2>8. ЗАКЛЮЧИТЕЛЬНЫЕ ПОЛОЖЕНИЯ</h2>
        <p><strong>8.1.</strong> Соглашение вступает в силу с момента начала использования Сервиса.</p>
        <p><strong>8.2.</strong> При возникновении споров стороны стремятся к их разрешению путем переговоров.</p>

        <div class="footer">
            <p><strong>Дата последнего обновления:</strong> 15.01.2025</p>
            <p><strong>По вопросам обращайтесь:</strong> @MiddleCloud1</p>
        </div>
    </div>
</body>
</html>
"""

@app.route('/agreement')
def agreement():
    """Страница пользовательского соглашения"""
    return render_template_string(AGREEMENT_TEMPLATE)

@app.route('/health')
def health():
    """Проверка здоровья сервиса"""
    return {"status": "healthy"}

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8081)