#!/usr/bin/env python3
"""
Обновление бота для запроса email
"""

# Добавить в класс OrderStates:
# waiting_email = State()

# Добавить в setup_handlers():
# self.dp.message.register(
#     self.process_email_input,
#     OrderStates.waiting_email
# )

# Заменить process_plan_selection на:
async def process_plan_selection(self, callback: types.CallbackQuery, state: FSMContext):
    """Обработка выбора тарифа"""
    plan_id = callback.data.split("_")[1]
    plan = VPN_PLANS.get(plan_id)
    
    if not plan:
        await callback.answer("❌ Неверный тариф")
        return
    
    # Сохраняем выбранный план и запрашиваем email
    await state.update_data(plan_id=plan_id)
    await state.set_state(OrderStates.waiting_email)
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="buy_vpn")]
    ])
    
    await callback.message.edit_text(
        f"📧 <b>Введите ваш email для чека:</b>\n\n"
        f"📦 Тариф: {plan['name']} - {plan['price']}₽\n"
        f"⏰ Срок: {plan['days']} дней\n\n"
        "Отправьте ваш email сообщением:",
        reply_markup=keyboard,
        parse_mode="HTML"
    )

# Добавить новую функцию:
async def process_email_input(self, message: types.Message, state: FSMContext):
    """Обработка ввода email"""
    email = message.text.strip()
    
    if "@" not in email or "." not in email:
        await message.answer("❌ Некорректный email. Попробуйте ещё раз:")
        return
        
    data = await state.get_data()
    plan_id = data.get("plan_id")
    plan = VPN_PLANS.get(plan_id)
    
    if not plan:
        await message.answer("❌ Ошибка. Начните сначала.")
        await state.clear()
        return
        
    payment = await self.create_payment(
        plan["price"], 
        f"VPN {plan['name']}",
        message.from_user.id,
        email
    )
    
    if payment:
        order_id = db.create_order(
            user_id=message.from_user.id,
            plan_id=plan_id,
            payment_id=payment.id,
            amount=plan["price"]
        )
        
        await state.update_data(
            plan_id=plan_id,
            payment_id=payment.id,
            user_id=message.from_user.id,
            order_id=order_id,
            user_email=email
        )
        await state.set_state(OrderStates.waiting_payment)
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(
                text="💳 Оплатить", 
                url=payment.confirmation.confirmation_url
            )],
            [InlineKeyboardButton(
                text="✅ Проверить оплату", 
                callback_data=f"check_{payment.id}"
            )]
        ])
        
        await message.answer(
            f"💰 <b>К оплате:</b> {plan['price']}₽\n"
            f"📦 <b>Тариф:</b> {plan['name']}\n"
            f"📧 <b>Email:</b> {email}\n\n"
            "Нажмите кнопку для оплаты:",
            reply_markup=keyboard,
            parse_mode="HTML"
        )
    else:
        await message.answer("❌ Ошибка создания платежа")

print("Теперь пользователь будет вводить свой email для чека!")