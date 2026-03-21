from django.db import models


class TelegramAudienceGroup(models.Model):
    name = models.CharField("Название группы", max_length=120, unique=True)
    description = models.TextField("Пояснение", blank=True)

    class Meta:
        ordering = ["name"]
        verbose_name = "Группа подписчиков Telegram"
        verbose_name_plural = "Группы подписчиков Telegram"

    def __str__(self):
        return self.name


class TelegramChatCollection(models.Model):
    name = models.CharField("Название объединения", max_length=120, unique=True)
    description = models.TextField("Пояснение", blank=True)
    chats = models.ManyToManyField(
        "TelegramSubscriber",
        verbose_name="Telegram-группы",
        related_name="chat_collections",
        blank=True,
    )

    class Meta:
        ordering = ["name"]
        verbose_name = "Объединение Telegram-групп"
        verbose_name_plural = "Объединения Telegram-групп"

    def __str__(self):
        return self.name


class TelegramSubscriber(models.Model):
    CHAT_TYPE_PRIVATE = "private"
    CHAT_TYPE_GROUP = "group"
    CHAT_TYPE_SUPERGROUP = "supergroup"
    CHAT_TYPE_CHANNEL = "channel"
    CHAT_TYPE_CHOICES = [
        (CHAT_TYPE_PRIVATE, "Личный чат"),
        (CHAT_TYPE_GROUP, "Группа"),
        (CHAT_TYPE_SUPERGROUP, "Супергруппа"),
        (CHAT_TYPE_CHANNEL, "Канал"),
    ]

    chat_id = models.BigIntegerField("Chat ID", unique=True)
    chat_type = models.CharField(
        "Тип чата",
        max_length=20,
        choices=CHAT_TYPE_CHOICES,
        default=CHAT_TYPE_PRIVATE,
    )
    chat_title = models.CharField("Название чата", max_length=255, blank=True)
    username = models.CharField("Username", max_length=255, blank=True)
    first_name = models.CharField("Имя", max_length=255, blank=True)
    last_name = models.CharField("Фамилия", max_length=255, blank=True)
    language_code = models.CharField("Язык", max_length=32, blank=True)
    groups = models.ManyToManyField(
        TelegramAudienceGroup,
        verbose_name="Группы подписчиков",
        related_name="subscribers",
        blank=True,
    )
    is_active = models.BooleanField("Получает уведомления", default=True)
    is_blocked = models.BooleanField("Бот заблокирован", default=False)
    started_at = models.DateTimeField("Подписался", auto_now_add=True)
    last_interaction_at = models.DateTimeField("Последняя активность", auto_now=True)

    class Meta:
        ordering = ["-last_interaction_at"]
        verbose_name = "Получатель Telegram"
        verbose_name_plural = "Получатели Telegram"

    def __str__(self):
        return self.display_name

    @property
    def display_name(self):
        if self.chat_type != self.CHAT_TYPE_PRIVATE:
            return self.chat_title or str(self.chat_id)

        if self.username:
            return f"@{self.username}"

        full_name = " ".join(part for part in [self.first_name, self.last_name] if part)
        return full_name or str(self.chat_id)

    @property
    def is_group_chat(self):
        return self.chat_type in {self.CHAT_TYPE_GROUP, self.CHAT_TYPE_SUPERGROUP}


class TelegramBroadcast(models.Model):
    TARGET_MODE_CHOICES = [
        ("all", "Всем подписчикам"),
        ("groups", "Только выбранным группам"),
        ("group_chats", "Только Telegram-группам"),
    ]

    title = models.CharField("Заголовок уведомления", max_length=220)
    message = models.TextField("Текст уведомления")
    link_url = models.URLField("Ссылка", blank=True)
    target_mode = models.CharField(
        "Кому отправлять",
        max_length=20,
        choices=TARGET_MODE_CHOICES,
        default="all",
    )
    target_groups = models.ManyToManyField(
        TelegramAudienceGroup,
        verbose_name="Группы получателей",
        related_name="broadcasts",
        blank=True,
    )
    target_chat_collections = models.ManyToManyField(
        TelegramChatCollection,
        verbose_name="Объединения Telegram-групп",
        related_name="broadcasts",
        blank=True,
    )
    include_group_chats = models.BooleanField(
        "Также отправить в группы Telegram",
        default=False,
        help_text="Сообщение уйдёт и в те группы, где есть бот и группа активирована командой.",
    )
    is_sent = models.BooleanField("Уже отправлено", default=False)
    sent_count = models.PositiveIntegerField("Успешно отправлено", default=0)
    failed_count = models.PositiveIntegerField("Не удалось отправить", default=0)
    last_error = models.TextField("Последняя ошибка", blank=True)
    created_at = models.DateTimeField("Создано", auto_now_add=True)
    updated_at = models.DateTimeField("Изменено", auto_now=True)
    sent_at = models.DateTimeField("Отправлено", blank=True, null=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Уведомление в Telegram"
        verbose_name_plural = "Уведомления в Telegram"

    def __str__(self):
        return self.title
