"""
Методы для админских функций
"""

async def admin_gift_key(self, callback: types.CallbackQuery, state: FSMContext):
    """Начало процесса подарка ключа"""
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer("❌ Доступ запрещен")
        return
        
    await state.set_state(AdminStates.waiting_gift_user_id)
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="❌ Отмена", callback_data="admin_panel")]
    ])
    
    await callback.message.edit_text(
        "🎁 <b>Подарок ключа</b>\n\n"
        "Введите Telegram ID пользователя:",
        reply_markup=keyboard,
        parse_mode="HTML"
    )
    
async def process_gift_user_id(self, message: types.Message, state: FSMContext):
    """Обработка ID пользователя для подарка"""
    try:
        user_id = int(message.text)
        await state.update_data(gift_user_id=user_id)
        await state.set_state(AdminStates.waiting_gift_days)
        
        await message.answer(
            f"🎁 <b>Подарок для пользователя {user_id}</b>\n\n"
            "Введите количество дней подписки:",
            parse_mode="HTML"
        )
    except ValueError:
        await message.answer("❌ Неверный ID. Введите число.")
        
async def process_gift_days(self, message: types.Message, state: FSMContext):
    """Обработка количества дней для подарка"""
    try:
        days = int(message.text)
        if days <= 0:
            await message.answer("❌ Количество дней должно быть больше 0.")
            return
            
        data = await state.get_data()
        user_id = data.get('gift_user_id')
        if not user_id:
            await message.answer("❌ Ошибка: ID пользователя не найден")
            await state.clear()
            return
        
        vpn_result = await self.create_gift_vpn_client(user_id, days)
        
        if vpn_result:
            vpn_config, email, expires_at = vpn_result
            
            db.add_vpn_key(
                user_id=user_id,
                order_id=None,
                email=email,
                config=vpn_config,
                expires_at=expires_at,
                traffic_limit=0
            )
            
            try:
                await self.bot.send_message(
                    user_id,
                    f"🎁 <b>Подарок от администрации!</b>\n\n"
                    f"🔑 <b>Ваш VPN ключ:</b>\n"
                    f"<code>{vpn_config}</code>\n\n"
                    f"⏰ <b>Действует до:</b> {expires_at.strftime('%d.%m.%Y %H:%M')}\n\n"
                    "📱 Используйте /help для инструкции по подключению",
                    parse_mode="HTML"
                )
                
                await message.answer(
                    f"✅ <b>Подарок отправлен!</b>\n\n"
                    f"👤 Пользователь: {user_id}\n"
                    f"⏰ Период: {days} дней",
                    parse_mode="HTML"
                )
            except Exception as e:
                await message.answer(
                    f"❌ Ошибка отправки пользователю {user_id}: {e}\n\n"
                    f"🔑 <b>Ключ создан:</b>\n"
                    f"<code>{vpn_config}</code>",
                    parse_mode="HTML"
                )
        else:
            await message.answer("❌ Ошибка создания VPN ключа")
            
        await state.clear()
        
    except ValueError:
        await message.answer("❌ Неверное количество дней. Введите число.")
        
async def admin_gift_link(self, callback: types.CallbackQuery, state: FSMContext):
    """Начало создания подарочной ссылки"""
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer("❌ Доступ запрещен")
        return
        
    await state.set_state(AdminStates.waiting_gift_link_days)
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="❌ Отмена", callback_data="admin_panel")]
    ])
    
    await callback.message.edit_text(
        "🎁 <b>Подарочная ссылка</b>\n\n"
        "Введите количество дней подписки:",
        reply_markup=keyboard,
        parse_mode="HTML"
    )
    
async def process_gift_link_days(self, message: types.Message, state: FSMContext):
    """Обработка создания подарочной ссылки"""
    try:
        days = int(message.text)
        if days <= 0:
            await message.answer("❌ Количество дней должно быть больше 0.")
            return
            
        gift_code = f"gift_{uuid.uuid4().hex[:8]}"
        
        # Сохраняем в БД
        if db.create_gift_link(gift_code, days):
            bot_username = (await self.bot.get_me()).username
            gift_link = f"https://t.me/{bot_username}?start={gift_code}"
            
            await message.answer(
                f"✅ <b>Подарочная ссылка создана!</b>\n\n"
                f"🎁 <b>Период:</b> {days} дней\n"
                f"🔗 <b>Ссылка:</b>\n"
                f"<code>{gift_link}</code>\n\n"
                f"📝 <b>Код:</b> <code>{gift_code}</code>",
                parse_mode="HTML"
            )
        else:
            await message.answer("❌ Ошибка создания подарочной ссылки")
        
        await state.clear()
        
    except ValueError:
        await message.answer("❌ Неверное количество дней. Введите число.")
        
async def create_gift_vpn_client(self, user_id: int, days: int) -> Optional[tuple]:
    """Создание подарочного VPN клиента"""
    email = f"gift_{user_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    
    async with XrayManager(XRAY_API_URL) as xray:
        result = await xray.add_client(email, {"days": days})
        
        if result:
            return (result["config"], result["email"], result["expires_at"])
        else:
            logger.error(f"Не удалось создать подарочный VPN клиента для {email}")
            return None