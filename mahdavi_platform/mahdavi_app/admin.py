# admin.py
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.utils.html import format_html
from .models import *

# ===============================
# توابع عمومی
# ===============================

def make_active(modeladmin, request, queryset):
    queryset.update(is_active=True)
make_active.short_description = "فعال کردن موارد انتخاب شده"

def make_inactive(modeladmin, request, queryset):
    queryset.update(is_active=False)
make_inactive.short_description = "غیرفعال کردن موارد انتخاب شده"

# ===============================
# کلاس‌های پایه
# ===============================

class BaseAdmin(admin.ModelAdmin):
    actions = [make_active, make_inactive]

# ===============================
# بخش ۱: مدیریت کاربران و پروفایل
# ===============================

class CustomUserAdmin(UserAdmin):
    list_display = ['get_full_name', 'phone', 'age', 'age_group', 'points', 'join_date', 'is_active']
    list_filter = ['age_group', 'spiritual_level', 'is_staff', 'is_superuser', 'is_active', 'join_date']
    search_fields = ['first_name', 'last_name', 'phone']
    ordering = ['-join_date']
    actions = [make_active, make_inactive]
    
    fieldsets = (
        ('اطلاعات ورود', {'fields': ('phone', 'password')}),
        ('اطلاعات شخصی', {
            'fields': ('first_name', 'last_name', 'age', 'age_group', 'profile_image', 'bio')
        }),
        ('اطلاعات مهدوی', {
            'fields': ('spiritual_level', 'points')
        }),
        ('دسترسی‌ها', {
            'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions'),
        }),
    )
    
    readonly_fields = ['join_date', 'last_login', 'date_joined', 'age_group']
    
    def get_full_name(self, obj):
        return obj.get_full_name()
    get_full_name.short_description = 'نام کامل'

# ===============================
# بخش ۲: شبکه اجتماعی
# ===============================

class PostAdmin(BaseAdmin):
    list_display = ['user', 'content_type', 'likes_count', 'comments_count', 'created_at', 'is_active']
    list_filter = ['content_type', 'is_active', 'created_at']
    search_fields = ['caption', 'user__first_name', 'user__last_name']
    list_editable = ['is_active']

class StoryAdmin(BaseAdmin):
    list_display = ['user', 'content_type', 'views_count', 'created_at', 'expires_at', 'is_active']
    list_filter = ['content_type', 'is_active', 'created_at']
    search_fields = ['caption', 'user__first_name', 'user__last_name']

# ===============================
# بخش ۳: کتابخانه
# ===============================

class BookCategoryAdmin(BaseAdmin):
    list_display = ['name', 'order', 'is_active', 'books_count', 'created_at']
    list_filter = ['is_active', 'created_at']
    list_editable = ['order', 'is_active']
    search_fields = ['name', 'description']
    
    def books_count(self, obj):
        return obj.books.count()
    books_count.short_description = 'تعداد کتاب‌ها'

class BookAdmin(BaseAdmin):
    list_display = ['title', 'author', 'category', 'book_type', 'status', 'is_featured', 'is_active', 'created_at']
    list_filter = ['category', 'book_type', 'status', 'is_featured', 'is_active', 'created_at']
    list_editable = ['status', 'is_featured', 'is_active']
    search_fields = ['title', 'author', 'description']
    
    fieldsets = (
        ('اطلاعات اصلی کتاب', {
            'fields': (
                'title', 'author', 'description', 'short_description', 'category', 
                'book_type', 'cover_image', 'status', 'is_featured', 'is_active', 'order'
            )
        }),
        ('فایل‌ها', {
            'fields': ('pdf_file', 'audio_files')
        }),
        ('قیمت‌گذاری', {
            'fields': ('price',)  
        }),
        ('اطلاعات فنی', {
            'fields': ('pages', 'publisher', 'isbn', 'publish_year')
        }),
    )

# ===============================
# بخش ۴: ایستگاه‌های آموزشی
# ===============================

class StationAdmin(BaseAdmin):
    list_display = ['name', 'order', 'points_required', 'is_active', 'get_allowed_age_groups']
    list_filter = ['is_active', 'allowed_age_groups']
    search_fields = ['name', 'description']
    ordering = ['order']
    list_editable = ['order', 'points_required', 'is_active']
    
    fieldsets = (
        ('اطلاعات اصلی ایستگاه', {
            'fields': (
                'name', 'description', 'quran_verse', 'order', 
                'points_required', 'image', 'is_active', 'allowed_age_groups'
            )
        }),
        ('محتوای داستان', {
            'fields': ('story_content', 'story_points')
        }),
        ('محتوای دعا', {
            'fields': ('prayer_content', 'prayer_points')
        }),
        ('محتوای مطلب', {
            'fields': ('article_content', 'article_points')
        }),
        ('محتوای ویدیو', {
            'fields': ('video_file', 'video_points')
        }),
        ('سوال چهارگزینه‌ای', {
            'fields': (
                'quiz_question', 
                'choice1', 'choice2', 'choice3', 'choice4',
                'correct_choice', 'quiz_points'
            )
        }),
    )
    
    def get_allowed_age_groups(self, obj):
        if obj.allowed_age_groups:
            return ", ".join([dict(CustomUser.AGE_GROUPS).get(ag, ag) for ag in obj.allowed_age_groups.split(',')])
        return "-"
    get_allowed_age_groups.short_description = 'گروه‌های سنی مجاز'

# ===============================
# بخش ۵: بازی‌ها
# ===============================

class GameAdmin(BaseAdmin):
    list_display = ['title', 'status', 'is_active', 'points_reward', 'order', 'created_date']
    list_filter = ['status', 'is_active', 'created_date', 'allowed_age_groups']
    list_editable = ['status', 'is_active', 'points_reward', 'order']
    search_fields = ['title', 'description']

# ===============================
# بخش ۶: فروشگاه
# ===============================

class ProductCategoryAdmin(BaseAdmin):
    list_display = ['name', 'order', 'is_active', 'products_count', 'created_at']
    list_filter = ['is_active', 'created_at']
    list_editable = ['order', 'is_active']
    search_fields = ['name', 'description']
    
    def products_count(self, obj):
        return obj.products.count()
    products_count.short_description = 'تعداد محصولات'

class ProductAdmin(BaseAdmin):
    list_display = ['name', 'category', 'final_price', 'stock_quantity', 'status', 'is_featured', 'is_active', 'created_at']
    list_filter = ['category', 'status', 'is_featured', 'is_active', 'created_at']
    list_editable = ['stock_quantity', 'status', 'is_featured', 'is_active']
    search_fields = ['name', 'description']
    
    def final_price(self, obj):
        return obj.get_final_price()
    final_price.short_description = 'قیمت نهایی'

# ===============================
# بخش ۷: خیریه
# ===============================

class CharityProjectAdmin(BaseAdmin):
    list_display = ['title', 'category', 'target_amount', 'current_amount', 'status', 'is_featured', 'created_at']
    list_filter = ['category', 'status', 'is_featured', 'is_urgent', 'is_active', 'created_at']
    search_fields = ['title', 'description', 'location']
    list_editable = ['status', 'is_featured']

# ===============================
# ثبت مدل‌ها با گروه‌بندی دستی
# ===============================

# گروه ۱: کاربران و پروفایل
admin.site.register(CustomUser, CustomUserAdmin)
admin.site.register(SocialProfile, BaseAdmin)
admin.site.register(Follow, BaseAdmin)
admin.site.register(FollowRequest, BaseAdmin)

# گروه ۲: شبکه اجتماعی
admin.site.register(Post, PostAdmin)
admin.site.register(Story, StoryAdmin)
admin.site.register(PostLike, BaseAdmin)
admin.site.register(Comment, BaseAdmin)
admin.site.register(CommentLike, BaseAdmin)
admin.site.register(StoryView, BaseAdmin)

# گروه ۳: کتابخانه
admin.site.register(BookCategory, BookCategoryAdmin)
admin.site.register(Book, BookAdmin)
admin.site.register(BookOrder, BaseAdmin)
admin.site.register(UserBookAccess, BaseAdmin)

# گروه ۴: ایستگاه‌های آموزشی
admin.site.register(AgeGroupSettings, BaseAdmin)
admin.site.register(Station, StationAdmin)
admin.site.register(UserProgress, BaseAdmin)
admin.site.register(Badge, BaseAdmin)
admin.site.register(UserBadge, BaseAdmin)

# گروه ۵: بازی‌ها
admin.site.register(Game, GameAdmin)
admin.site.register(UserGameProgress, BaseAdmin)

# گروه ۶: چت و ارتباطات
admin.site.register(ChatRoom, BaseAdmin)
admin.site.register(ChatMessage, BaseAdmin)
admin.site.register(MessageReadReceipt, BaseAdmin)

# گروه ۷: محتوای چندرسانه‌ای
admin.site.register(AudioFile, BaseAdmin)

# گروه ۸: فروشگاه
admin.site.register(ProductCategory, ProductCategoryAdmin)
admin.site.register(Product, ProductAdmin)
admin.site.register(ProductReview, BaseAdmin)
admin.site.register(Order, BaseAdmin)
admin.site.register(Wishlist, BaseAdmin)
admin.site.register(Cart, BaseAdmin)

# گروه ۹: تورهای مجازی
admin.site.register(VirtualTourCategory, BaseAdmin)
admin.site.register(VirtualTour, BaseAdmin)

# گروه ۱۰: خیریه
admin.site.register(CharityCategory, BaseAdmin)
admin.site.register(CharityProject, CharityProjectAdmin)
admin.site.register(CharityDonation, BaseAdmin)
admin.site.register(CharityUpdate, BaseAdmin)
admin.site.register(CharityVolunteer, BaseAdmin)
admin.site.register(CharityImage, BaseAdmin)

# ===============================
# تنظیمات پنل ادمین
# ===============================

admin.site.site_header = '🕌 پنل مدیریت پلتفرم مهدوی'
admin.site.site_title = 'پلتفرم مهدوی'
admin.site.index_title = 'مدیریت محتوای پلتفرم مهدوی'