from django.db import models
from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.utils import timezone
from django.core.validators import RegexValidator, MinValueValidator
from django.urls import reverse

class CustomUserManager(BaseUserManager):
    def create_user(self, phone, first_name, last_name, age, email=None, password=None, **extra_fields):
        print(f"🔧 create_user called with: phone={phone}, email={email}")  # دیباگ
        
        if not phone:
            raise ValueError('شماره موبایل باید وارد شود')
        if not first_name:
            raise ValueError('نام باید وارد شود')
        if not last_name:
            raise ValueError('نام خانوادگی باید وارد شود')
        if not age:
            raise ValueError('سن باید وارد شود')
        
        # بررسی یکتایی شماره موبایل
        if self.model.objects.filter(phone=phone).exists():
            raise ValueError('این شماره موبایل قبلاً ثبت شده است')
        
        # بررسی ایمیل اگر ارائه شده باشد
        if email:
            if self.model.objects.filter(email=email).exists():
                raise ValueError('این ایمیل قبلاً ثبت شده است')
            email = self.normalize_email(email)
        
        print(f"✅ تمام بررسی‌ها passed")
        
        user = self.model(
            phone=phone,
            first_name=first_name,
            last_name=last_name,
            age=age,
            email=email,
            **extra_fields
        )
        
        user.set_password(password)
        user.save(using=self._db)
        print(f"✅ کاربر ذخیره شد: {user}")
        return user

    def create_superuser(self, phone, first_name, last_name, age, email=None, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_active', True)
        extra_fields.setdefault('email_verified', True)
        
        if extra_fields.get('is_staff') is not True:
            raise ValueError('کاربر فوق‌ادمین باید is_staff=True باشد.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('کاربر فوق‌ادمین باید is_superuser=True باشد.')
        
        return self.create_user(phone, first_name, last_name, age, email, password, **extra_fields)

class CustomUser(AbstractUser):
    SPIRITUAL_LEVELS = [
        ('novice', 'نوآموز مهدوی'),
        ('lover', 'عاشق مهدوی'),
        ('assistant', 'یاور مهدوی'),
        ('ambassador', 'سفیر مهدوی'),
    ]
    
    AGE_GROUPS = [
        ('child', 'کودک (3-9 سال)'),
        ('junior', 'نوجوان (10-14 سال)'),
        ('youth', 'جوان (15-18 سال)'),
        ('adult', 'بزرگسال (18+ سال)'),
    ]
    
    first_name = models.CharField(max_length=30, verbose_name="نام")
    last_name = models.CharField(max_length=30, verbose_name="نام خانوادگی")
    age = models.IntegerField(verbose_name="سن")
    age_group = models.CharField(max_length=10, choices=AGE_GROUPS, blank=True, verbose_name="گروه سنی")
    
    phone_regex = RegexValidator(regex=r'^09\d{9}$', message="شماره موبایل باید با 09 شروع شود و 11 رقم باشد")
    phone = models.CharField(max_length=11, validators=[phone_regex], unique=True, verbose_name="شماره موبایل")
    
    # اضافه کردن فیلد ایمیل
    email = models.EmailField(unique=True, verbose_name="ایمیل", null=True, blank=True)
    email_verified = models.BooleanField(default=False, verbose_name="ایمیل تایید شده")
    email_verification_code = models.CharField(max_length=6, blank=True, verbose_name="کد تایید ایمیل")
    verification_code_sent_at = models.DateTimeField(null=True, blank=True, verbose_name="زمان ارسال کد")
    
    # فیلدهای مربوط به بازیابی رمز عبور
    reset_password_code = models.CharField(max_length=6, blank=True, verbose_name="کد بازیابی رمز عبور")
    reset_code_sent_at = models.DateTimeField(null=True, blank=True, verbose_name="زمان ارسال کد بازیابی")
    
    spiritual_level = models.CharField(max_length=20, choices=SPIRITUAL_LEVELS, default='novice', verbose_name="سطح معنوی")
    points = models.IntegerField(default=0, verbose_name="امتیازها")
    join_date = models.DateTimeField(default=timezone.now, verbose_name="تاریخ عضویت")
    profile_image = models.ImageField(upload_to='profiles/', null=True, blank=True, verbose_name="تصویر پروفایل")
    bio = models.TextField(max_length=500, blank=True, verbose_name="بیوگرافی")
    
    username = None
    
    USERNAME_FIELD = 'phone'
    REQUIRED_FIELDS = ['first_name', 'last_name', 'age']  # ایمیل اجباری نیست
    
    objects = CustomUserManager()
    
    groups = models.ManyToManyField(
        'auth.Group',
        blank=True,
        related_name="mahdavi_user_set",
        related_query_name="mahdavi_user",
        verbose_name="گروه‌ها"
    )
    user_permissions = models.ManyToManyField(
        'auth.Permission',
        blank=True,
        related_name="mahdavi_user_set",
        related_query_name="mahdavi_user",
        verbose_name="دسترسی‌ها"
    )
    
    class Meta:
        verbose_name = 'کاربر'
        verbose_name_plural = 'کاربران'
    
    def __str__(self):
        return f"{self.first_name} {self.last_name} - {self.get_age_group_display()}"
    
    def get_full_name(self):
        return f"{self.first_name} {self.last_name}"
    
    def save(self, *args, **kwargs):
        # تعیین گروه سنی بر اساس سن
        if self.age <= 9:
            self.age_group = 'child'
        elif self.age <= 14:
            self.age_group = 'junior'
        elif self.age <= 18:
            self.age_group = 'youth'
        else:
            self.age_group = 'adult'
        super().save(*args, **kwargs)
    
    def generate_verification_code(self):
        """تولید کد تایید 6 رقمی"""
        import random
        return ''.join([str(random.randint(0, 9)) for _ in range(6)])
    
    def generate_reset_code(self):
        """تولید کد بازیابی 6 رقمی"""
        import random
        return ''.join([str(random.randint(0, 9)) for _ in range(6)])

class AgeGroupSettings(models.Model):
    age_group = models.CharField(max_length=10, choices=CustomUser.AGE_GROUPS, unique=True, verbose_name="گروه سنی")
    theme_color = models.CharField(max_length=7, default='#3B82F6', verbose_name="رنگ تم")
    theme_name = models.CharField(max_length=100, verbose_name="نام تم")
    description = models.TextField(blank=True, verbose_name="توضیحات")
    is_active = models.BooleanField(default=True, verbose_name="فعال")
    
    class Meta:
        verbose_name = "تنظیمات گروه سنی"
        verbose_name_plural = "تنظیمات گروه‌های سنی"
    
    def __str__(self):
        return self.get_age_group_display()

class Station(models.Model):
    name = models.CharField(max_length=100, verbose_name="نام")
    description = models.TextField(verbose_name="توضیحات")
    quran_verse = models.TextField(blank=True, verbose_name="آیه قرآن")
    order = models.IntegerField(verbose_name="ترتیب")
    is_active = models.BooleanField(default=True, verbose_name="فعال")
    image = models.ImageField(upload_to='stations/', null=True, blank=True, verbose_name="تصویر")
    points_required = models.IntegerField(default=0, verbose_name="امتیاز مورد نیاز")
    
    # گروه‌های سنی مجاز برای این ایستگاه
    allowed_age_groups = models.CharField(
        max_length=50,
        default='child,junior,youth,adult',
        verbose_name="گروه‌های سنی مجاز"
    )
    
    story_content = models.TextField(blank=True, verbose_name="محتوای داستان")
    story_points = models.IntegerField(default=10, verbose_name="امتیاز داستان")
    prayer_content = models.TextField(blank=True, verbose_name="محتوای دعا")
    prayer_points = models.IntegerField(default=15, verbose_name="امتیاز دعا")
    article_content = models.TextField(blank=True, verbose_name="محتوای مطلب")
    article_points = models.IntegerField(default=10, verbose_name="امتیاز مطلب")
    video_file = models.FileField(upload_to='videos/', null=True, blank=True, verbose_name="فایل ویدیو")
    video_points = models.IntegerField(default=20, verbose_name="امتیاز ویدیو")
    
    quiz_question = models.TextField(blank=True, verbose_name="سوال آزمون")
    choice1 = models.CharField(max_length=200, blank=True, verbose_name="گزینه ۱")
    choice2 = models.CharField(max_length=200, blank=True, verbose_name="گزینه ۲")
    choice3 = models.CharField(max_length=200, blank=True, verbose_name="گزینه ۳")
    choice4 = models.CharField(max_length=200, blank=True, verbose_name="گزینه ۴")
    correct_choice = models.IntegerField(choices=[(1, 'گزینه ۱'), (2, 'گزینه ۲'), (3, 'گزینه ۳'), (4, 'گزینه ۴')], null=True, blank=True, verbose_name="گزینه صحیح")
    quiz_points = models.IntegerField(default=20, verbose_name="امتیاز آزمون")
    
    class Meta:
        ordering = ['order']
        verbose_name = 'ایستگاه'
        verbose_name_plural = 'ایستگاه‌ها'
    
    def __str__(self):
        return self.name
    
    def save(self, *args, **kwargs):
        if not self.video_file:
            self.video_points = 0
        super().save(*args, **kwargs)
    
    def get_active_contents_count(self):
        count = 0
        if self.story_content and self.story_content.strip():
            count += 1
        if self.prayer_content and self.prayer_content.strip():
            count += 1
        if self.article_content and self.article_content.strip():
            count += 1
        if self.video_file:
            count += 1
        if self.quiz_question and self.quiz_question.strip():
            count += 1
        return count
    
    def is_allowed_for_age_group(self, age_group):
        return age_group in self.allowed_age_groups.split(',')

class UserProgress(models.Model):
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, verbose_name="کاربر")
    station = models.ForeignKey(Station, on_delete=models.CASCADE, verbose_name="ایستگاه")
    completed_story = models.BooleanField(default=False, verbose_name="داستان تکمیل شده")
    completed_prayer = models.BooleanField(default=False, verbose_name="دعا تکمیل شده")
    completed_article = models.BooleanField(default=False, verbose_name="مطلب تکمیل شده")
    completed_video = models.BooleanField(default=False, verbose_name="ویدیو تکمیل شده")
    completed_quiz = models.BooleanField(default=False, verbose_name="آزمون تکمیل شده")
    quiz_passed = models.BooleanField(default=False, verbose_name="آزمون قبول شده")
    completion_date = models.DateTimeField(null=True, blank=True, verbose_name="تاریخ تکمیل")
    total_score = models.IntegerField(default=0, verbose_name="امتیاز کل")
    
    class Meta:
        unique_together = ['user', 'station']
        verbose_name = 'پیشرفت کاربر'
        verbose_name_plural = 'پیشرفت‌های کاربران'
    
    def __str__(self):
        return f"{self.user.get_full_name()} - {self.station.name}"
    
    def get_progress_percentage(self):
        station = self.station
        total_contents = station.get_active_contents_count()
        if total_contents == 0:
            return 0
        
        completed_count = 0
        if station.story_content.strip() and self.completed_story:
            completed_count += 1
        if station.prayer_content.strip() and self.completed_prayer:
            completed_count += 1
        if station.article_content.strip() and self.completed_article:
            completed_count += 1
        if station.video_file and self.completed_video:
            completed_count += 1
        if station.quiz_question.strip() and self.completed_quiz:
            completed_count += 1
            
        return (completed_count / total_contents) * 100

class Badge(models.Model):
    name = models.CharField(max_length=100, verbose_name="نام")
    description = models.TextField(verbose_name="توضیحات")
    image = models.ImageField(upload_to='badges/', verbose_name="تصویر")
    points_required = models.IntegerField(default=0, verbose_name="امتیاز مورد نیاز")
    stations_required = models.IntegerField(default=0, verbose_name="ایستگاه‌های مورد نیاز")
    is_active = models.BooleanField(default=True, verbose_name="فعال")
    
    # گروه‌های سنی مجاز برای این نشان
    allowed_age_groups = models.CharField(
        max_length=50,
        default='child,junior,youth,adult',
        verbose_name="گروه‌های سنی مجاز"
    )
    
    class Meta:
        verbose_name = 'نشان'
        verbose_name_plural = 'نشان‌ها'
    
    def __str__(self):
        return self.name

class UserBadge(models.Model):
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, verbose_name="کاربر")
    badge = models.ForeignKey(Badge, on_delete=models.CASCADE, verbose_name="نشان")
    awarded_date = models.DateTimeField(auto_now_add=True, verbose_name="تاریخ اعطا")
    
    class Meta:
        unique_together = ['user', 'badge']
        verbose_name = 'نشان کاربر'
        verbose_name_plural = 'نشان‌های کاربران'
    
    def __str__(self):
        return f"{self.user.get_full_name()} - {self.badge.name}"

class Game(models.Model):
    STATUS_CHOICES = [
        ('draft', 'پیش‌نویس'),
        ('published', 'منتشر شده'),
    ]
    
    title = models.CharField(max_length=200, verbose_name="عنوان")
    description = models.TextField(verbose_name="توضیحات")
    html_file = models.FileField(upload_to='games/html/', verbose_name="فایل HTML")
    thumbnail = models.ImageField(upload_to='games/thumbnails/', null=True, blank=True, verbose_name="تصویر بندانگشتی")
    points_reward = models.IntegerField(default=10, verbose_name="پاداش امتیاز")
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='draft', verbose_name="وضعیت")
    is_active = models.BooleanField(default=True, verbose_name="فعال")
    created_date = models.DateTimeField(auto_now_add=True, verbose_name="تاریخ ایجاد")
    order = models.IntegerField(default=0, verbose_name="ترتیب")
    
    # گروه‌های سنی مجاز برای این بازی
    allowed_age_groups = models.CharField(
        max_length=50,
        default='child,junior,youth,adult',
        verbose_name="گروه‌های سنی مجاز"
    )
    
    class Meta:
        verbose_name = 'بازی'
        verbose_name_plural = 'بازی‌ها'
        ordering = ['order', '-created_date']
    
    def __str__(self):
        return self.title

class UserGameProgress(models.Model):
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, verbose_name="کاربر")
    game = models.ForeignKey(Game, on_delete=models.CASCADE, verbose_name="بازی")
    completed = models.BooleanField(default=False, verbose_name="تکمیل شده")
    score = models.IntegerField(default=0, verbose_name="امتیاز")
    play_count = models.IntegerField(default=0, verbose_name="تعداد بازی")
    last_played = models.DateTimeField(null=True, blank=True, verbose_name="آخرین بازی")
    completion_date = models.DateTimeField(null=True, blank=True, verbose_name="تاریخ تکمیل")
    
    class Meta:
        unique_together = ['user', 'game']
        verbose_name = 'پیشرفت بازی کاربر'
        verbose_name_plural = 'پیشرفت‌های بازی کاربران'
    
    def __str__(self):
        return f"{self.user.get_full_name()} - {self.game.title}"

class ChatRoom(models.Model):
    ROOM_TYPES = [
        ('private', 'خصوصی'),
        ('group', 'گروهی'),
    ]
    
    name = models.CharField(max_length=100, verbose_name="نام")
    room_type = models.CharField(max_length=10, choices=ROOM_TYPES, default='private', verbose_name="نوع اتاق")
    description = models.TextField(blank=True, verbose_name="توضیحات")
    created_by = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='created_rooms', verbose_name="ایجاد شده توسط")
    participants = models.ManyToManyField(CustomUser, related_name='chat_rooms', verbose_name="شرکت‌کنندگان")
    admins = models.ManyToManyField(CustomUser, related_name='admin_rooms', blank=True, verbose_name="مدیران")
    is_active = models.BooleanField(default=True, verbose_name="فعال")
    created_date = models.DateTimeField(auto_now_add=True, verbose_name="تاریخ ایجاد")
    last_activity = models.DateTimeField(auto_now=True, verbose_name="آخرین فعالیت")
    
    class Meta:
        verbose_name = 'اتاق چت'
        verbose_name_plural = 'اتاق‌های چت'
        ordering = ['-last_activity']
    
    def __str__(self):
        return self.name
    
    def get_participants_count(self):
        return self.participants.count()
    
    def is_user_admin(self, user):
        return self.admins.filter(id=user.id).exists()
    
    def can_user_manage(self, user):
        return self.created_by == user or self.is_user_admin(user)

class ChatMessage(models.Model):
    MESSAGE_TYPES = [
        ('text', 'متن'),
        ('image', 'عکس'),
        ('file', 'فایل'),
        ('audio', 'صوت'),
        ('video', 'ویدیو'),
        ('sticker', 'استیکر'),
        ('system', 'سیستمی'),
    ]
    
    room = models.ForeignKey(ChatRoom, on_delete=models.CASCADE, related_name='messages', verbose_name="اتاق")
    sender = models.ForeignKey(CustomUser, on_delete=models.CASCADE, verbose_name="فرستنده")
    message_type = models.CharField(max_length=10, choices=MESSAGE_TYPES, default='text', verbose_name="نوع پیام")
    content = models.TextField(blank=True, verbose_name="محتوا")
    image = models.ImageField(upload_to='chat/images/%Y/%m/%d/', null=True, blank=True, verbose_name="عکس")
    file = models.FileField(upload_to='chat/files/%Y/%m/%d/', null=True, blank=True, verbose_name="فایل")
    audio = models.FileField(upload_to='chat/audio/%Y/%m/%d/', null=True, blank=True, verbose_name="صوت")
    video = models.FileField(upload_to='chat/video/%Y/%m/%d/', null=True, blank=True, verbose_name="ویدیو")
    sticker = models.CharField(max_length=100, blank=True, verbose_name="استیکر")
    file_name = models.CharField(max_length=255, blank=True, verbose_name="نام فایل")
    file_size = models.IntegerField(default=0, verbose_name="اندازه فایل")
    is_read = models.BooleanField(default=False, verbose_name="خوانده شده")
    created_date = models.DateTimeField(auto_now_add=True, verbose_name="تاریخ ایجاد")
    
    class Meta:
        verbose_name = 'پیام چت'
        verbose_name_plural = 'پیام‌های چت'
        ordering = ['created_date']
    
    def __str__(self):
        return f"{self.sender.get_full_name()} - {self.content[:50]}"
    
    def get_file_size_display(self):
        if self.file_size < 1024:
            return f"{self.file_size} B"
        elif self.file_size < 1024 * 1024:
            return f"{self.file_size / 1024:.1f} KB"
        else:
            return f"{self.file_size / (1024 * 1024):.1f} MB"

class MessageReadReceipt(models.Model):
    message = models.ForeignKey(ChatMessage, on_delete=models.CASCADE, related_name='read_receipts', verbose_name="پیام")
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, verbose_name="کاربر")
    read_date = models.DateTimeField(auto_now_add=True, verbose_name="تاریخ خواندن")
    
    class Meta:
        unique_together = ['message', 'user']
        verbose_name = 'رسید خواندن پیام'
        verbose_name_plural = 'رسیدهای خواندن پیام'

class AudioFile(models.Model):
    title = models.CharField(max_length=200, verbose_name="عنوان")
    audio_file = models.FileField(upload_to='audio/', verbose_name="فایل صوتی")
    is_active = models.BooleanField(default=True, verbose_name="فعال")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="تاریخ ایجاد")
    
    # گروه‌های سنی مجاز برای این فایل صوتی
    allowed_age_groups = models.CharField(
        max_length=50,
        default='child,junior,youth,adult',
        verbose_name="گروه‌های سنی مجاز"
    )
    
    class Meta:
        verbose_name = "فایل صوتی"
        verbose_name_plural = "فایل‌های صوتی"
        ordering = ['-created_at']
    
    def __str__(self):
        return self.title
    
    def save(self, *args, **kwargs):
        # اگر این فایل فعال شود، سایر فایل‌ها غیرفعال می‌شوند
        if self.is_active:
            AudioFile.objects.exclude(pk=self.pk).update(is_active=False)
        super().save(*args, **kwargs)

class ProductCategory(models.Model):
    name = models.CharField(max_length=100, verbose_name="نام دسته‌بندی")
    description = models.TextField(blank=True, verbose_name="توضیحات")
    image = models.ImageField(upload_to='categories/', null=True, blank=True, verbose_name="تصویر دسته‌بندی")
    is_active = models.BooleanField(default=True, verbose_name="فعال")
    order = models.IntegerField(default=0, verbose_name="ترتیب نمایش")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="تاریخ ایجاد")
    
    class Meta:
        verbose_name = "دسته‌بندی محصول"
        verbose_name_plural = "دسته‌بندی‌های محصولات"
        ordering = ['order', 'name']
    
    def __str__(self):
        return self.name
    
    def get_absolute_url(self):
        return reverse('product_list') + f'?category={self.id}'
    
    def get_products_count(self):
        return self.products.filter(is_active=True, status='published').count()

class Product(models.Model):
    STATUS_CHOICES = [
        ('draft', 'پیش‌نویس'),
        ('published', 'منتشر شده'),
        ('out_of_stock', 'ناموجود'),
    ]
    
    name = models.CharField(max_length=200, verbose_name="نام محصول")
    description = models.TextField(verbose_name="توضیحات محصول")
    short_description = models.TextField(max_length=300, blank=True, verbose_name="توضیح مختصر")
    price = models.DecimalField(
        max_digits=10, 
        decimal_places=0, 
        verbose_name="قیمت (تومان)",
        validators=[MinValueValidator(0)]
    )
    discounted_price = models.DecimalField(
        max_digits=10, 
        decimal_places=0, 
        null=True, 
        blank=True, 
        verbose_name="قیمت تخفیف‌خورده",
        validators=[MinValueValidator(0)]
    )
    category = models.ForeignKey(
        ProductCategory, 
        on_delete=models.CASCADE, 
        related_name='products', 
        verbose_name="دسته‌بندی"
    )
    main_image = models.ImageField(upload_to='products/main/', verbose_name="تصویر اصلی")
    stock_quantity = models.IntegerField(
        default=0, 
        verbose_name="تعداد موجودی",
        validators=[MinValueValidator(0)]
    )
    status = models.CharField(max_length=15, choices=STATUS_CHOICES, default='draft', verbose_name="وضعیت")
    is_featured = models.BooleanField(default=False, verbose_name="محصول ویژه")
    is_active = models.BooleanField(default=True, verbose_name="فعال")
    order = models.IntegerField(default=0, verbose_name="ترتیب نمایش")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="تاریخ ایجاد")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="تاریخ بروزرسانی")
    
    # گروه‌های سنی مجاز برای این محصول
    allowed_age_groups = models.CharField(
        max_length=50,
        default='child,junior,youth,adult',
        verbose_name="گروه‌های سنی مجاز"
    )
    
    class Meta:
        verbose_name = "محصول"
        verbose_name_plural = "محصولات"
        ordering = ['order', '-created_at']
    
    def __str__(self):
        return self.name
    
    def get_absolute_url(self):
        return reverse('product_detail', kwargs={'product_id': self.id})
    
    def is_allowed_for_age_group(self, age_group):
        """بررسی دسترسی گروه سنی به محصول"""
        if not age_group:
            return True
        if not self.allowed_age_groups:
            return True
        return age_group in self.allowed_age_groups.split(',')
    
    @property
    def final_price(self):
        return self.discounted_price if self.discounted_price else self.price
    
    @property
    def has_discount(self):
        return self.discounted_price is not None and self.discounted_price < self.price
    
    @property
    def discount_percentage(self):
        if self.has_discount:
            return int(((self.price - self.discounted_price) / self.price) * 100)
        return 0
    
    @property
    def is_available(self):
        return (self.status == 'published' and 
                self.is_active and 
                self.stock_quantity > 0)
    
    def get_related_products(self, limit=4):
        """دریافت محصولات مرتبط"""
        return Product.objects.filter(
            category=self.category,
            is_active=True,
            status='published'
        ).exclude(id=self.id).order_by('?')[:limit]

class ProductImage(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='images', verbose_name="محصول")
    image = models.ImageField(upload_to='products/gallery/', verbose_name="تصویر")
    alt_text = models.CharField(max_length=200, blank=True, verbose_name="متن جایگزین")
    order = models.IntegerField(default=0, verbose_name="ترتیب نمایش")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="تاریخ ایجاد")
    
    class Meta:
        verbose_name = "تصویر محصول"
        verbose_name_plural = "تصاویر محصول"
        ordering = ['order', 'created_at']
    
    def __str__(self):
        return f"تصویر {self.product.name}"

class ProductReview(models.Model):
    RATING_CHOICES = [
        (1, '۱ ستاره'),
        (2, '۲ ستاره'),
        (3, '۳ ستاره'),
        (4, '۴ ستاره'),
        (5, '۵ ستاره'),
    ]
    
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='reviews', verbose_name="محصول")
    user = models.ForeignKey('CustomUser', on_delete=models.CASCADE, verbose_name="کاربر")
    rating = models.IntegerField(choices=RATING_CHOICES, verbose_name="امتیاز")
    comment = models.TextField(verbose_name="نظر")
    is_approved = models.BooleanField(default=False, verbose_name="تایید شده")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="تاریخ ایجاد")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="تاریخ بروزرسانی")
    
    class Meta:
        verbose_name = "نظر محصول"
        verbose_name_plural = "نظرات محصولات"
        unique_together = ['product', 'user']
        ordering = ['-created_at']
    
    def __str__(self):
        return f"نظر {self.user.get_full_name()} برای {self.product.name}"

class Wishlist(models.Model):
    user = models.ForeignKey('CustomUser', on_delete=models.CASCADE, related_name='wishlist_items', verbose_name="کاربر")
    product = models.ForeignKey(Product, on_delete=models.CASCADE, verbose_name="محصول")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="تاریخ ایجاد")
    
    class Meta:
        verbose_name = "لیست علاقه‌مندی"
        verbose_name_plural = "لیست‌های علاقه‌مندی"
        unique_together = ['user', 'product']
    
    def __str__(self):
        return f"{self.user.get_full_name()} - {self.product.name}"

class Cart(models.Model):
    user = models.ForeignKey('CustomUser', on_delete=models.CASCADE, related_name='cart_items', verbose_name="کاربر")
    product = models.ForeignKey(Product, on_delete=models.CASCADE, verbose_name="محصول")
    quantity = models.IntegerField(
        default=1, 
        verbose_name="تعداد",
        validators=[MinValueValidator(1)]
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="تاریخ ایجاد")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="تاریخ بروزرسانی")
    
    class Meta:
        verbose_name = "آیتم سبد خرید"
        verbose_name_plural = "آیتم‌های سبد خرید"
        unique_together = ['user', 'product']
    
    def __str__(self):
        return f"{self.user.get_full_name()} - {self.product.name} ({self.quantity})"
    
    @property
    def total_price(self):
        return self.product.final_price * self.quantity
    
    def can_increase_quantity(self):
        """بررسی امکان افزایش تعداد"""
        return self.quantity < self.product.stock_quantity

class Order(models.Model):
    STATUS_CHOICES = [
        ('pending', 'در انتظار پرداخت'),
        ('paid', 'پرداخت شده'),
        ('processing', 'در حال پردازش'),
        ('shipped', 'ارسال شده'),
        ('delivered', 'تحویل داده شده'),
        ('cancelled', 'لغو شده'),
        ('refunded', 'مرجوع شده'),
    ]
    
    PAYMENT_METHODS = [
        ('card_to_card', 'کارت به کارت'),
        ('online', 'پرداخت آنلاین'),
    ]
    
    order_number = models.CharField(max_length=20, unique=True, verbose_name="شماره سفارش")
    user = models.ForeignKey('CustomUser', on_delete=models.CASCADE, related_name='orders', verbose_name="کاربر")
    total_amount = models.DecimalField(
        max_digits=12, 
        decimal_places=0, 
        verbose_name="مبلغ کل",
        validators=[MinValueValidator(0)]
    )
    status = models.CharField(max_length=15, choices=STATUS_CHOICES, default='pending', verbose_name="وضعیت")
    payment_method = models.CharField(max_length=15, choices=PAYMENT_METHODS, default='card_to_card', verbose_name="روش پرداخت")
    
    # اطلاعات مشتری
    customer_name = models.CharField(max_length=100, verbose_name="نام مشتری")
    customer_phone = models.CharField(
        max_length=11, 
        verbose_name="تلفن مشتری",
        validators=[RegexValidator(regex=r'^09\d{9}$', message="شماره موبایل باید با 09 شروع شود و 11 رقم باشد")]
    )
    customer_address = models.TextField(verbose_name="آدرس")
    customer_postal_code = models.CharField(max_length=10, verbose_name="کد پستی")
    
    # اطلاعات پرداخت
    payment_receipt = models.ImageField(upload_to='payment_receipts/', null=True, blank=True, verbose_name="عکس رسید پرداخت")
    payment_date = models.DateTimeField(null=True, blank=True, verbose_name="تاریخ پرداخت")
    tracking_code = models.CharField(max_length=100, blank=True, verbose_name="کد رهگیری")
    
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="تاریخ ایجاد")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="تاریخ بروزرسانی")
    
    class Meta:
        verbose_name = "سفارش"
        verbose_name_plural = "سفارش‌ها"
        ordering = ['-created_at']
    
    def __str__(self):
        return f"سفارش {self.order_number} - {self.customer_name}"
    
    def save(self, *args, **kwargs):
        if not self.order_number:
            self.order_number = self.generate_order_number()
        super().save(*args, **kwargs)
    
    def generate_order_number(self):
        import random
        import string
        timestamp = timezone.now().strftime('%Y%m%d%H%M')
        random_str = ''.join(random.choices(string.digits, k=4))
        return f'ORD-{timestamp}-{random_str}'
    
    @property
    def items_count(self):
        return self.items.count()
    
    def get_status_display_class(self):
        """کلاس CSS برای نمایش وضعیت"""
        status_classes = {
            'pending': 'status-pending',
            'paid': 'status-paid',
            'processing': 'status-processing',
            'shipped': 'status-shipped',
            'delivered': 'status-delivered',
            'cancelled': 'status-cancelled',
            'refunded': 'status-refunded',
        }
        return status_classes.get(self.status, 'status-pending')

class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items', verbose_name="سفارش")
    product = models.ForeignKey(Product, on_delete=models.CASCADE, verbose_name="محصول")
    product_name = models.CharField(max_length=200, verbose_name="نام محصول")
    product_price = models.DecimalField(
        max_digits=10, 
        decimal_places=0, 
        verbose_name="قیمت محصول",
        validators=[MinValueValidator(0)]
    )
    quantity = models.IntegerField(
        verbose_name="تعداد",
        validators=[MinValueValidator(1)]
    )
    total_price = models.DecimalField(
        max_digits=10, 
        decimal_places=0, 
        verbose_name="قیمت کل",
        validators=[MinValueValidator(0)]
    )
    
    class Meta:
        verbose_name = "آیتم سفارش"
        verbose_name_plural = "آیتم‌های سفارش"
    
    def __str__(self):
        return f"{self.product_name} - {self.quantity} عدد"
    
    def save(self, *args, **kwargs):
        self.total_price = self.product_price * self.quantity
        super().save(*args, **kwargs)


class SocialProfile(models.Model):
    user = models.OneToOneField(CustomUser, on_delete=models.CASCADE, related_name='social_profile', verbose_name="کاربر")
    bio = models.TextField(max_length=500, blank=True, verbose_name="بیوگرافی")
    website = models.URLField(blank=True, verbose_name="وبسایت")
    is_private = models.BooleanField(default=False, verbose_name="حساب خصوصی")
    followers_count = models.IntegerField(default=0, verbose_name="تعداد دنبال‌کنندگان")
    following_count = models.IntegerField(default=0, verbose_name="تعداد دنبال‌شوندگان")
    posts_count = models.IntegerField(default=0, verbose_name="تعداد پست‌ها")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="تاریخ ایجاد")
    
    class Meta:
        verbose_name = "پروفایل اجتماعی"
        verbose_name_plural = "پروفایل‌های اجتماعی"
    
    def __str__(self):
        return f"پروفایل اجتماعی {self.user.get_full_name()}"

class Follow(models.Model):
    follower = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='following', verbose_name="دنبال‌کننده")
    following = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='followers', verbose_name="دنبال‌شونده")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="تاریخ ایجاد")
    
    class Meta:
        unique_together = ['follower', 'following']
        verbose_name = "دنبال‌کننده"
        verbose_name_plural = "دنبال‌کنندگان"
    
    def __str__(self):
        return f"{self.follower.get_full_name()} ← {self.following.get_full_name()}"

class Post(models.Model):
    CONTENT_TYPES = [
        ('text', 'متن'),
        ('image', 'عکس'),
        ('video', 'ویدیو'),
        ('audio', 'صوت'),
        ('prayer', 'دعا'),
        ('article', 'مطلب'),
    ]
    
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='posts', verbose_name="کاربر")
    content_type = models.CharField(max_length=10, choices=CONTENT_TYPES, default='text', verbose_name="نوع محتوا")
    caption = models.TextField(blank=True, verbose_name="کپشن")
    image = models.ImageField(upload_to='posts/images/%Y/%m/%d/', null=True, blank=True, verbose_name="عکس")
    video = models.FileField(upload_to='posts/videos/%Y/%m/%d/', null=True, blank=True, verbose_name="ویدیو")
    audio = models.FileField(upload_to='posts/audio/%Y/%m/%d/', null=True, blank=True, verbose_name="صوت")
    location = models.CharField(max_length=100, blank=True, verbose_name="مکان")
    is_active = models.BooleanField(default=True, verbose_name="فعال")
    likes_count = models.IntegerField(default=0, verbose_name="تعداد لایک‌ها")
    comments_count = models.IntegerField(default=0, verbose_name="تعداد نظرات")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="تاریخ ایجاد")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="تاریخ بروزرسانی")
    
    class Meta:
        verbose_name = "پست"
        verbose_name_plural = "پست‌ها"
        ordering = ['-created_at']
    
    def __str__(self):
        return f"پست {self.user.get_full_name()} - {self.get_content_type_display()}"

class PostLike(models.Model):
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='post_likes', verbose_name="کاربر")
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name='likes', verbose_name="پست")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="تاریخ ایجاد")
    
    class Meta:
        unique_together = ['user', 'post']
        verbose_name = "لایک پست"
        verbose_name_plural = "لایک‌های پست"
    
    def __str__(self):
        return f"{self.user.get_full_name()} لایک کرد {self.post.id}"

class Comment(models.Model):
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='comments', verbose_name="کاربر")
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name='comments', verbose_name="پست")
    parent = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True, related_name='replies', verbose_name="والد")
    text = models.TextField(verbose_name="متن نظر")
    likes_count = models.IntegerField(default=0, verbose_name="تعداد لایک‌ها")
    is_active = models.BooleanField(default=True, verbose_name="فعال")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="تاریخ ایجاد")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="تاریخ بروزرسانی")
    
    class Meta:
        verbose_name = "نظر"
        verbose_name_plural = "نظرات"
        ordering = ['created_at']
    
    def __str__(self):
        return f"نظر {self.user.get_full_name()} روی پست {self.post.id}"

class CommentLike(models.Model):
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='comment_likes', verbose_name="کاربر")
    comment = models.ForeignKey(Comment, on_delete=models.CASCADE, related_name='likes', verbose_name="نظر")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="تاریخ ایجاد")
    
    class Meta:
        unique_together = ['user', 'comment']
        verbose_name = "لایک نظر"
        verbose_name_plural = "لایک‌های نظر"
    
    def __str__(self):
        return f"{self.user.get_full_name()} لایک کرد نظر {self.comment.id}"

class Story(models.Model):
    CONTENT_TYPES = [
        ('image', 'عکس'),
        ('video', 'ویدیو'),
    ]
    
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='stories', verbose_name="کاربر")
    content_type = models.CharField(max_length=10, choices=CONTENT_TYPES, verbose_name="نوع محتوا")
    image = models.ImageField(upload_to='stories/images/%Y/%m/%d/', null=True, blank=True, verbose_name="عکس")
    video = models.FileField(upload_to='stories/videos/%Y/%m/%d/', null=True, blank=True, verbose_name="ویدیو")
    caption = models.TextField(blank=True, verbose_name="کپشن")
    is_active = models.BooleanField(default=True, verbose_name="فعال")
    views_count = models.IntegerField(default=0, verbose_name="تعداد بازدیدها")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="تاریخ ایجاد")
    expires_at = models.DateTimeField(verbose_name="تاریخ انقضا")
    
    class Meta:
        verbose_name = "استوری"
        verbose_name_plural = "استوری‌ها"
        ordering = ['-created_at']
    
    def __str__(self):
        return f"استوری {self.user.get_full_name()}"
    
    def save(self, *args, **kwargs):
        if not self.expires_at:
            from django.utils import timezone
            self.expires_at = timezone.now() + timezone.timedelta(hours=24)
        super().save(*args, **kwargs)
    
    @property
    def is_expired(self):
        from django.utils import timezone
        return timezone.now() > self.expires_at

class StoryView(models.Model):
    story = models.ForeignKey(Story, on_delete=models.CASCADE, related_name='views', verbose_name="استوری")
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='story_views', verbose_name="کاربر")
    viewed_at = models.DateTimeField(auto_now_add=True, verbose_name="تاریخ مشاهده")
    
    class Meta:
        unique_together = ['story', 'user']
        verbose_name = "بازدید استوری"
        verbose_name_plural = "بازدیدهای استوری"
    
    def __str__(self):
        return f"{self.user.get_full_name()} مشاهده کرد {self.story.id}"

class FollowRequest(models.Model):
    from_user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='sent_requests', verbose_name="از کاربر")
    to_user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='received_requests', verbose_name="به کاربر")
    is_accepted = models.BooleanField(default=False, verbose_name="تایید شده")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="تاریخ ایجاد")
    
    class Meta:
        unique_together = ['from_user', 'to_user']
        verbose_name = "درخواست دنبال کردن"
        verbose_name_plural = "درخواست‌های دنبال کردن"
    
    def __str__(self):
        return f"{self.from_user.get_full_name()} → {self.to_user.get_full_name()}"

class BookCategory(models.Model):
    name = models.CharField(max_length=100, verbose_name="نام دسته‌بندی")
    description = models.TextField(blank=True, verbose_name="توضیحات")
    is_active = models.BooleanField(default=True, verbose_name="فعال")
    order = models.IntegerField(default=0, verbose_name="ترتیب نمایش")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="تاریخ ایجاد")
    
    class Meta:
        verbose_name = "دسته‌بندی کتاب"
        verbose_name_plural = "دسته‌بندی‌های کتاب"
        ordering = ['order', 'name']
    
    def __str__(self):
        return self.name

class Book(models.Model):
    BOOK_TYPES = [
        ('free', 'رایگان'),
        ('purchase', 'فروشی'),
    ]
    
    STATUS_CHOICES = [
        ('draft', 'پیش‌نویس'),
        ('published', 'منتشر شده'),
    ]
    
    title = models.CharField(max_length=200, verbose_name="عنوان کتاب")
    author = models.CharField(max_length=100, verbose_name="نویسنده")
    description = models.TextField(verbose_name="توضیحات")
    short_description = models.TextField(max_length=300, blank=True, verbose_name="توضیح مختصر")
    category = models.ForeignKey(BookCategory, on_delete=models.CASCADE, related_name='books', verbose_name="دسته‌بندی")
    book_type = models.CharField(max_length=10, choices=BOOK_TYPES, default='free', verbose_name="نوع کتاب")
    
    # فایل‌ها
    pdf_file = models.FileField(upload_to='books/pdf/', verbose_name="فایل PDF")
    cover_image = models.ImageField(upload_to='books/covers/', verbose_name="تصویر جلد")
    
    # فایل‌های صوتی (اختیاری)
    audio_files = models.FileField(upload_to='books/audio/', null=True, blank=True, verbose_name="فایل‌های صوتی")
    
    # قیمت
    price = models.DecimalField(max_digits=10, decimal_places=0, default=0, verbose_name="قیمت (تومان)")
    
    # اطلاعات فنی
    pages = models.IntegerField(default=0, verbose_name="تعداد صفحات")
    publisher = models.CharField(max_length=100, blank=True, verbose_name="ناشر")
    isbn = models.CharField(max_length=20, blank=True, verbose_name="شابک")
    publish_year = models.IntegerField(null=True, blank=True, verbose_name="سال انتشار")
    
    # وضعیت
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='draft', verbose_name="وضعیت")
    is_featured = models.BooleanField(default=False, verbose_name="کتاب ویژه")
    is_active = models.BooleanField(default=True, verbose_name="فعال")
    order = models.IntegerField(default=0, verbose_name="ترتیب نمایش")
    
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="تاریخ ایجاد")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="تاریخ بروزرسانی")
    
    class Meta:
        verbose_name = "کتاب"
        verbose_name_plural = "کتاب‌ها"
        ordering = ['order', '-created_at']
    
    def __str__(self):
        return self.title
    
    @property
    def is_free(self):
        return self.book_type == 'free'
    
    @property
    def can_purchase(self):
        return self.book_type == 'purchase'
    
    @property
    def final_price(self):
        return self.price
    
    @property
    def is_available(self):
        return self.status == 'published' and self.is_active

class BookOrder(models.Model):
    STATUS_CHOICES = [
        ('pending', 'در انتظار پرداخت'),
        ('paid', 'پرداخت شده'),
        ('approved', 'تایید شده'),
        ('rejected', 'رد شده'),
    ]
    
    order_number = models.CharField(max_length=20, unique=True, verbose_name="شماره سفارش")
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='book_orders', verbose_name="کاربر")
    book = models.ForeignKey(Book, on_delete=models.CASCADE, verbose_name="کتاب")
    
    # اطلاعات قیمت
    unit_price = models.DecimalField(max_digits=10, decimal_places=0, verbose_name="قیمت واحد")
    total_amount = models.DecimalField(max_digits=10, decimal_places=0, verbose_name="مبلغ کل")
    
    # اطلاعات پرداخت
    payment_receipt = models.ImageField(upload_to='book_payments/', null=True, blank=True, verbose_name="عکس رسید پرداخت")
    payment_date = models.DateTimeField(null=True, blank=True, verbose_name="تاریخ پرداخت")
    
    # وضعیت
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pending', verbose_name="وضعیت")
    admin_notes = models.TextField(blank=True, verbose_name="یادداشت ادمین")
    
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="تاریخ ایجاد")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="تاریخ بروزرسانی")
    
    class Meta:
        verbose_name = "سفارش کتاب"
        verbose_name_plural = "سفارش‌های کتاب"
        ordering = ['-created_at']
    
    def __str__(self):
        return f"سفارش {self.order_number} - {self.user.get_full_name()}"
    
    def save(self, *args, **kwargs):
        if not self.order_number:
            self.order_number = self.generate_order_number()
        super().save(*args, **kwargs)
    
    def generate_order_number(self):
        import random
        import string
        timestamp = timezone.now().strftime('%Y%m%d%H%M')
        random_str = ''.join(random.choices(string.digits, k=4))
        return f'BOOK-{timestamp}-{random_str}'
    
    @property
    def can_download(self):
        """آیا کاربر می‌تواند کتاب را دانلود کند؟"""
        return self.status == 'approved'

class UserBookAccess(models.Model):
    """مدل برای مدیریت دسترسی‌های کاربر به کتاب‌ها"""
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, verbose_name="کاربر")
    book = models.ForeignKey(Book, on_delete=models.CASCADE, verbose_name="کتاب")
    order = models.ForeignKey(BookOrder, on_delete=models.CASCADE, verbose_name="سفارش")
    granted_at = models.DateTimeField(auto_now_add=True, verbose_name="زمان اعطای دسترسی")
    is_active = models.BooleanField(default=True, verbose_name="فعال")
    
    class Meta:
        verbose_name = "دسترسی کاربر به کتاب"
        verbose_name_plural = "دسترسی‌های کاربران به کتاب‌ها"
        unique_together = ['user', 'book']
    
    def __str__(self):
        return f"{self.user.get_full_name()} - {self.book.title}"
    
    @property
    def can_access(self):
        return self.is_active

# اضافه کردن به انتهای فایل models.py

class VirtualTourCategory(models.Model):
    name = models.CharField(max_length=100, verbose_name="نام دسته‌بندی")
    description = models.TextField(blank=True, verbose_name="توضیحات")
    icon = models.CharField(max_length=50, blank=True, verbose_name="آیکون")
    color = models.CharField(max_length=7, default='#3B82F6', verbose_name="رنگ")
    order = models.IntegerField(default=0, verbose_name="ترتیب نمایش")
    is_active = models.BooleanField(default=True, verbose_name="فعال")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="تاریخ ایجاد")
    
    class Meta:
        verbose_name = "دسته‌بندی تور مجازی"
        verbose_name_plural = "دسته‌بندی‌های تور مجازی"
        ordering = ['order', 'name']
    
    def __str__(self):
        return self.name

class VirtualTour(models.Model):
    STATUS_CHOICES = [
        ('draft', 'پیش‌نویس'),
        ('published', 'منتشر شده'),
    ]
    
    title = models.CharField(max_length=200, verbose_name="عنوان تور")
    description = models.TextField(blank=True, verbose_name="توضیحات")
    category = models.ForeignKey(VirtualTourCategory, on_delete=models.CASCADE, 
                               related_name='tours', verbose_name="دسته‌بندی")
    
    # تغییر به URLField به جای TextField
    embed_url = models.URLField(verbose_name="آدرس URL تور مجازی", 
                               help_text="آدرس کامل تور مجازی (مثال: https://example.com/tour)")
    
    thumbnail = models.ImageField(upload_to='virtual_tours/thumbnails/', verbose_name="تصویر بندانگشتی")
    duration = models.CharField(max_length=50, blank=True, verbose_name="مدت زمان تور")
    location = models.CharField(max_length=100, blank=True, verbose_name="مکان")
    tags = models.CharField(max_length=200, blank=True, verbose_name="برچسب‌ها")
    view_count = models.IntegerField(default=0, verbose_name="تعداد بازدید")
    order = models.IntegerField(default=0, verbose_name="ترتیب نمایش")
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='draft', verbose_name="وضعیت")
    is_featured = models.BooleanField(default=False, verbose_name="تور ویژه")
    is_active = models.BooleanField(default=True, verbose_name="فعال")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="تاریخ ایجاد")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="تاریخ بروزرسانی")
    
    class Meta:
        verbose_name = "تور مجازی"
        verbose_name_plural = "تورهای مجازی"
        ordering = ['order', '-created_at']
    
    def __str__(self):
        return self.title
    
    @property
    def is_published(self):
        return self.status == 'published' and self.is_active
    
    def increment_view_count(self):
        """افزایش تعداد بازدید"""
        self.view_count += 1
        self.save()

# اضافه کردن به انتهای فایل models.py

class CharityCategory(models.Model):
    """دسته‌بندی‌های خیریه"""
    name = models.CharField(max_length=100, verbose_name="نام دسته‌بندی")
    description = models.TextField(verbose_name="توضیحات")
    icon = models.CharField(max_length=50, blank=True, verbose_name="آیکون")
    color = models.CharField(max_length=7, default='#3B82F6', verbose_name="رنگ")
    image = models.ImageField(upload_to='charity/categories/', null=True, blank=True, verbose_name="تصویر")
    is_active = models.BooleanField(default=True, verbose_name="فعال")
    order = models.IntegerField(default=0, verbose_name="ترتیب نمایش")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="تاریخ ایجاد")
    
    class Meta:
        verbose_name = "دسته‌بندی خیریه"
        verbose_name_plural = "دسته‌بندی‌های خیریه"
        ordering = ['order', 'name']
    
    def __str__(self):
        return self.name

class CharityProject(models.Model):
    """پروژه‌های خیریه"""
    STATUS_CHOICES = [
        ('draft', 'پیش‌نویس'),
        ('active', 'فعال'),
        ('completed', 'تکمیل شده'),
        ('paused', 'متوقف شده'),
    ]
    
    title = models.CharField(max_length=200, verbose_name="عنوان پروژه")
    description = models.TextField(verbose_name="توضیحات کامل")
    short_description = models.TextField(max_length=300, verbose_name="توضیح مختصر")
    category = models.ForeignKey(CharityCategory, on_delete=models.CASCADE, 
                               related_name='projects', verbose_name="دسته‌بندی")
    
    # اهداف مالی
    target_amount = models.DecimalField(
        max_digits=15, 
        decimal_places=0, 
        verbose_name="مبلغ هدف (تومان)",
        validators=[MinValueValidator(0)]
    )
    current_amount = models.DecimalField(
        max_digits=15, 
        decimal_places=0, 
        default=0,
        verbose_name="مبلغ جمع‌آوری شده (تومان)",
        validators=[MinValueValidator(0)]
    )
    
    # اطلاعات پروژه
    start_date = models.DateField(verbose_name="تاریخ شروع")
    end_date = models.DateField(null=True, blank=True, verbose_name="تاریخ پایان")
    location = models.CharField(max_length=100, verbose_name="مکان اجرا")
    beneficiary_count = models.IntegerField(default=0, verbose_name="تعداد بهره‌برداران")
    
    # رسانه‌ها
    main_image = models.ImageField(upload_to='charity/projects/', verbose_name="تصویر اصلی")
    gallery_images = models.ManyToManyField('CharityImage', blank=True, verbose_name="گالری تصاویر")
    
    # وضعیت
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='draft', verbose_name="وضعیت")
    is_featured = models.BooleanField(default=False, verbose_name="پروژه ویژه")
    is_urgent = models.BooleanField(default=False, verbose_name="پروژه فوری")
    is_active = models.BooleanField(default=True, verbose_name="فعال")
    
    # اطلاعات بانکی
    card_number = models.CharField(max_length=16, verbose_name="شماره کارت")
    card_holder = models.CharField(max_length=100, verbose_name="صاحب کارت")
    bank_name = models.CharField(max_length=100, verbose_name="نام بانک")
    
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="تاریخ ایجاد")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="تاریخ بروزرسانی")
    
    class Meta:
        verbose_name = "پروژه خیریه"
        verbose_name_plural = "پروژه‌های خیریه"
        ordering = ['-created_at']
    
    def __str__(self):
        return self.title
    
    @property
    def progress_percentage(self):
        """درصد پیشرفت جمع‌آوری کمک‌ها"""
        if self.target_amount == 0:
            return 0
        return min(100, (self.current_amount / self.target_amount) * 100)
    
    @property
    def remaining_amount(self):
        """مبلغ باقی‌مانده"""
        return max(0, self.target_amount - self.current_amount)
    
    @property
    def days_remaining(self):
        """روزهای باقی‌مانده"""
        from django.utils import timezone
        if self.end_date:
            remaining = (self.end_date - timezone.now().date()).days
            return max(0, remaining)
        return None
    
    @property
    def donors_count(self):
        """تعداد کمک‌کنندگان"""
        return CharityDonation.objects.filter(project=self, status='completed').count()
    
    def update_current_amount(self):
        """به‌روزرسانی مبلغ جمع‌آوری شده"""
        completed_donations = CharityDonation.objects.filter(
            project=self, 
            status='completed'
        ).aggregate(total=models.Sum('amount'))['total'] or 0
        self.current_amount = completed_donations
        self.save()

class CharityImage(models.Model):
    """تصاویر گالری پروژه‌های خیریه"""
    project = models.ForeignKey(CharityProject, on_delete=models.CASCADE, 
                              related_name='images', verbose_name="پروژه")
    image = models.ImageField(upload_to='charity/gallery/%Y/%m/%d/', verbose_name="تصویر")
    caption = models.CharField(max_length=200, blank=True, verbose_name="عنوان")
    order = models.IntegerField(default=0, verbose_name="ترتیب نمایش")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="تاریخ ایجاد")
    
    class Meta:
        verbose_name = "تصویر خیریه"
        verbose_name_plural = "تصاویر خیریه"
        ordering = ['order', 'created_at']
    
    def __str__(self):
        return f"تصویر {self.project.title}"

class CharityDonation(models.Model):
    """کمک‌های مردمی"""
    STATUS_CHOICES = [
        ('pending', 'در انتظار پرداخت'),
        ('paid', 'پرداخت شده'),
        ('verified', 'تایید شده'),
        ('rejected', 'رد شده'),
        ('refunded', 'مرجوع شده'),
    ]
    
    donation_number = models.CharField(max_length=20, unique=True, verbose_name="شماره کمک")
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, 
                           related_name='charity_donations', verbose_name="کمک‌کننده")
    project = models.ForeignKey(CharityProject, on_delete=models.CASCADE, 
                              related_name='donations', verbose_name="پروژه")
    
    # اطلاعات کمک
    amount = models.DecimalField(
        max_digits=12, 
        decimal_places=0, 
        verbose_name="مبلغ کمک (تومان)",
        validators=[MinValueValidator(1000)]  # حداقل 1000 تومان
    )
    is_anonymous = models.BooleanField(default=False, verbose_name="ناشناس")
    message = models.TextField(blank=True, verbose_name="پیام کمک‌کننده")
    
    # اطلاعات پرداخت
    payment_receipt = models.ImageField(upload_to='charity/receipts/%Y/%m/%d/', 
                                      null=True, blank=True, verbose_name="عکس رسید پرداخت")
    payment_date = models.DateTimeField(null=True, blank=True, verbose_name="تاریخ پرداخت")
    tracking_code = models.CharField(max_length=100, blank=True, verbose_name="کد رهگیری")
    
    # وضعیت
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pending', verbose_name="وضعیت")
    admin_notes = models.TextField(blank=True, verbose_name="یادداشت ادمین")
    
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="تاریخ ایجاد")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="تاریخ بروزرسانی")
    
    class Meta:
        verbose_name = "کمک خیریه"
        verbose_name_plural = "کمک‌های خیریه"
        ordering = ['-created_at']
    
    def __str__(self):
        return f"کمک {self.donation_number} - {self.user.get_full_name()}"
    
    def save(self, *args, **kwargs):
        if not self.donation_number:
            self.donation_number = self.generate_donation_number()
        super().save(*args, **kwargs)
        
        # به‌روزرسانی مبلغ جمع‌آوری شده پروژه
        if self.status == 'completed':
            self.project.update_current_amount()
    
    def generate_donation_number(self):
        import random
        import string
        timestamp = timezone.now().strftime('%Y%m%d%H%M')
        random_str = ''.join(random.choices(string.digits, k=4))
        return f'DON-{timestamp}-{random_str}'
    
    @property
    def donor_name(self):
        """نام کمک‌کننده (در صورت ناشناس بودن)"""
        if self.is_anonymous:
            return "ناشناس"
        return self.user.get_full_name()

class CharityUpdate(models.Model):
    """به‌روزرسانی‌های پروژه‌های خیریه"""
    UPDATE_TYPES = [
        ('progress', 'پیشرفت کار'),
        ('financial', 'گزارش مالی'),
        ('general', 'به‌روزرسانی عمومی'),
        ('completion', 'اتمام پروژه'),
    ]
    
    project = models.ForeignKey(CharityProject, on_delete=models.CASCADE, 
                              related_name='updates', verbose_name="پروژه")
    title = models.CharField(max_length=200, verbose_name="عنوان")
    content = models.TextField(verbose_name="محتوا")
    update_type = models.CharField(max_length=10, choices=UPDATE_TYPES, default='general', verbose_name="نوع به‌روزرسانی")
    
    # رسانه‌ها
    image = models.ImageField(upload_to='charity/updates/%Y/%m/%d/', null=True, blank=True, verbose_name="تصویر")
    video = models.FileField(upload_to='charity/updates/videos/%Y/%m/%d/', null=True, blank=True, verbose_name="ویدیو")
    
    # اطلاعات مالی (برای گزارش‌های مالی)
    spent_amount = models.DecimalField(
        max_digits=12, 
        decimal_places=0, 
        null=True, blank=True,
        verbose_name="مبلغ هزینه شده (تومан)"
    )
    expense_description = models.TextField(blank=True, verbose_name="توضیحات هزینه")
    
    created_by = models.ForeignKey(CustomUser, on_delete=models.CASCADE, verbose_name="ایجاد کننده")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="تاریخ ایجاد")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="تاریخ بروزرسانی")
    
    class Meta:
        verbose_name = "به‌روزرسانی خیریه"
        verbose_name_plural = "به‌روزرسانی‌های خیریه"
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.title} - {self.project.title}"

class CharityVolunteer(models.Model):
    """داوطلبان خیریه"""
    STATUS_CHOICES = [
        ('pending', 'در انتظار تایید'),
        ('active', 'فعال'),
        ('rejected', 'رد شده'),
        ('inactive', 'غیرفعال'),
    ]
    
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, 
                           related_name='charity_volunteers', verbose_name="کاربر")
    project = models.ForeignKey(CharityProject, on_delete=models.CASCADE, 
                              related_name='volunteers', verbose_name="پروژه")
    
    motivation = models.TextField(verbose_name="انگیزه همکاری")
    skills = models.TextField(blank=True, verbose_name="مهارت‌ها")
    available_hours = models.IntegerField(default=0, verbose_name="ساعات قابل اختصاص در هفته")
    
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pending', verbose_name="وضعیت")
    admin_notes = models.TextField(blank=True, verbose_name="یادداشت ادمین")
    
    applied_at = models.DateTimeField(auto_now_add=True, verbose_name="تاریخ درخواست")
    approved_at = models.DateTimeField(null=True, blank=True, verbose_name="تاریخ تایید")
    
    class Meta:
        verbose_name = "داوطلب خیریه"
        verbose_name_plural = "داوطلبان خیریه"
        unique_together = ['user', 'project']
    
    def __str__(self):
        return f"{self.user.get_full_name()} - {self.project.title}"