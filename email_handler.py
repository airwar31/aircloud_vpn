#!/usr/bin/env python3
"""
Обработчик ввода email для платежей
"""

async def process_email_input(self, message: types.Message, state: FSMContext):
    """Обработка ввода email"""
    email = message.text.strip()
    
    # Простая проверка email
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
        
    # Создание платежа с email
    payment = await self.create_payment(
        plan["price"], 
        f"VPN {plan['name']}",
        message.from_user.id,
        email
    )
    
    if payment:
        # Создаем заказ в БД
        order_id = db.create_order(
            user_id=message.from_user.id,
            plan_id=plan_id,
            payment_id=payment.id,
            amount=plan["price"]
        )
        
        if not order_id:
            await message.answer("❌ Ошибка создания заказа")
            return
        
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
            )],
            [InlineKeyboardButton(
                text="⬅️ Назад", 
                callback_data="back_menu"
            )]
        ])
        
        await message.answer(
            f"💰 <b>К оплате:</b> {plan['price']}₽\n"
            f"📦 <b>Тариф:</b> {plan['name']}\n"
            f"⏰ <b>Срок:</b> {plan['days']} дней\n"
            f"📧 <b>Email для чека:</b> {email}\n"
            f"🔥 <b>Трафик:</b> безлимитный\n\n"
            "Нажмите кнопку для оплаты:",
            reply_markup=keyboard,
            parse_mode="HTML"
        )
    else:
        await message.answer("❌ Ошибка создания платежа")