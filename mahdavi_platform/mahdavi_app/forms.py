from django import forms
from django.core.validators import RegexValidator
from .models import *

class LoginForm(forms.Form):
    phone_regex = RegexValidator(regex=r'^09\d{9}$', message="شماره موبایل باید با 09 شروع شود و 11 رقم باشد")
    
    phone = forms.CharField(
        label='شماره موبایل',
        validators=[phone_regex],
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': '09xxxxxxxxx', 'maxlength': '11'})
    )
    password = forms.CharField(
        label='رمز عبور',
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'رمز عبور خود را وارد کنید'})
    )

class RegisterForm(forms.Form):
    phone_regex = RegexValidator(regex=r'^09\d{9}$', message="شماره موبایل باید با 09 شروع شود و 11 رقم باشد")
    
    first_name = forms.CharField(
        label='نام',
        max_length=30,
        widget=forms.TextInput(attrs={
            'class': 'form-control', 
            'placeholder': 'نام خود را وارد کنید',
            'required': 'true'
        })
    )
    last_name = forms.CharField(
        label='نام خانوادگی',
        max_length=30,
        widget=forms.TextInput(attrs={
            'class': 'form-control', 
            'placeholder': 'نام خانوادگی خود را وارد کنید',
            'required': 'true'
        })
    )
    phone = forms.CharField(
        label='شماره موبایل',
        max_length=11,
        validators=[phone_regex],
        widget=forms.TextInput(attrs={
            'class': 'form-control', 
            'placeholder': '09xxxxxxxxx', 
            'maxlength': '11',
            'required': 'true'
        })
    )
    email = forms.EmailField(
        label='ایمیل',
        widget=forms.EmailInput(attrs={
            'class': 'form-control', 
            'placeholder': 'email@example.com',
            'required': 'true'
        })
    )
    age = forms.IntegerField(
        label='سن',
        min_value=3,
        max_value=120,
        widget=forms.NumberInput(attrs={
            'class': 'form-control', 
            'placeholder': 'سن خود را وارد کنید',
            'required': 'true'
        })
    )
    password = forms.CharField(
        label='رمز عبور',
        min_length=4,
        widget=forms.PasswordInput(attrs={
            'class': 'form-control', 
            'placeholder': 'رمز عبور خود را وارد کنید',
            'required': 'true'
        })
    )
    password2 = forms.CharField(
        label='تکرار رمز عبور',
        widget=forms.PasswordInput(attrs={
            'class': 'form-control', 
            'placeholder': 'رمز عبور خود را مجدداً وارد کنید',
            'required': 'true'
        })
    )
    
    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get('password')
        password2 = cleaned_data.get('password2')
        
        if password and password2 and password != password2:
            raise forms.ValidationError('رمزهای عبور مطابقت ندارند')
        
        phone = cleaned_data.get('phone')
        if phone and CustomUser.objects.filter(phone=phone).exists():
            raise forms.ValidationError('این شماره موبایل قبلاً ثبت شده است')
        
        email = cleaned_data.get('email')
        if email and CustomUser.objects.filter(email=email).exists():
            raise forms.ValidationError('این ایمیل قبلاً ثبت شده است')
        
        age = cleaned_data.get('age')
        if age and (age < 3 or age > 120):
            raise forms.ValidationError('سن باید بین 3 تا 120 سال باشد')
        
        return cleaned_data

class EmailVerificationForm(forms.Form):
    verification_code = forms.CharField(
        label='کد تایید',
        max_length=6,
        min_length=6,
        widget=forms.TextInput(attrs={
            'class': 'form-control', 
            'placeholder': 'کد 6 رقمی',
            'maxlength': '6',
            'pattern': '[0-9]{6}'
        })
    )

class ForgotPasswordForm(forms.Form):
    email = forms.EmailField(
        label='ایمیل',
        widget=forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'email@example.com'})
    )

class ResetPasswordForm(forms.Form):
    reset_code = forms.CharField(
        label='کد بازیابی',
        max_length=6,
        min_length=6,
        widget=forms.TextInput(attrs={
            'class': 'form-control', 
            'placeholder': 'کد 6 رقمی',
            'maxlength': '6',
            'pattern': '[0-9]{6}'
        })
    )
    new_password = forms.CharField(
        label='رمز عبور جدید',
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'رمز عبور جدید'})
    )
    confirm_password = forms.CharField(
        label='تکرار رمز عبور جدید',
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'تکرار رمز عبور جدید'})
    )
    
    def clean(self):
        cleaned_data = super().clean()
        new_password = cleaned_data.get('new_password')
        confirm_password = cleaned_data.get('confirm_password')
        
        if new_password and confirm_password and new_password != confirm_password:
            raise forms.ValidationError('رمزهای عبور جدید مطابقت ندارند')
        
        return cleaned_data

class ChangePasswordForm(forms.Form):
    current_password = forms.CharField(
        label='رمز عبور فعلی',
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'رمز عبور فعلی'})
    )
    new_password = forms.CharField(
        label='رمز عبور جدید',
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'رمز عبور جدید'})
    )
    confirm_password = forms.CharField(
        label='تکرار رمز عبور جدید',
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'تکرار رمز عبور جدید'})
    )
    
    def clean(self):
        cleaned_data = super().clean()
        new_password = cleaned_data.get('new_password')
        confirm_password = cleaned_data.get('confirm_password')
        
        if new_password and confirm_password and new_password != confirm_password:
            raise forms.ValidationError('رمزهای عبور جدید مطابقت ندارند')
        
        return cleaned_data

class ProfileForm(forms.ModelForm):
    class Meta:
        model = CustomUser
        fields = ['first_name', 'last_name', 'phone', 'age', 'profile_image', 'bio']
        widgets = {
            'first_name': forms.TextInput(attrs={'class': 'form-control'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control'}),
            'phone': forms.TextInput(attrs={'class': 'form-control', 'readonly': 'readonly'}),
            'age': forms.NumberInput(attrs={'class': 'form-control', 'min': '3', 'max': '120'}),
            'bio': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
            'profile_image': forms.FileInput(attrs={'class': 'form-control'}),
        }
        labels = {
            'first_name': 'نام',
            'last_name': 'نام خانوادگی',
            'phone': 'شماره موبایل',
            'age': 'سن',
            'profile_image': 'تصویر پروفایل',
            'bio': 'بیوگرافی',
        }

class AgeGroupSettingsForm(forms.ModelForm):
    class Meta:
        model = AgeGroupSettings
        fields = ['age_group', 'theme_color', 'theme_name', 'description', 'is_active']
        widgets = {
            'age_group': forms.Select(attrs={'class': 'form-control'}),
            'theme_color': forms.TextInput(attrs={'class': 'form-control', 'type': 'color'}),
            'theme_name': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
        labels = {
            'age_group': 'گروه سنی',
            'theme_color': 'رنگ تم',
            'theme_name': 'نام تم',
            'description': 'توضیحات',
            'is_active': 'فعال',
        }

class QuizForm(forms.Form):
    selected_choice = forms.ChoiceField(
        label='پاسخ خود را انتخاب کنید',
        choices=[],
        widget=forms.RadioSelect(attrs={'class': 'form-check-input'}),
        required=True
    )
    
    def __init__(self, *args, **kwargs):
        choices = kwargs.pop('choices', [])
        super().__init__(*args, **kwargs)
        self.fields['selected_choice'].choices = choices

class StationForm(forms.ModelForm):
    class Meta:
        model = Station
        fields = ['name', 'description', 'quran_verse', 'order', 'points_required', 'image', 'is_active', 'allowed_age_groups']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
            'quran_verse': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'order': forms.NumberInput(attrs={'class': 'form-control'}),
            'points_required': forms.NumberInput(attrs={'class': 'form-control'}),
            'image': forms.FileInput(attrs={'class': 'form-control'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'allowed_age_groups': forms.SelectMultiple(attrs={'class': 'form-control'}),
        }
        labels = {
            'name': 'نام ایستگاه',
            'description': 'توضیحات',
            'quran_verse': 'آیه قرآن',
            'order': 'ترتیب',
            'points_required': 'امتیاز مورد نیاز',
            'image': 'تصویر ایستگاه',
            'is_active': 'فعال',
            'allowed_age_groups': 'گروه های سنی مجاز',
        }

class GameForm(forms.ModelForm):
    class Meta:
        model = Game
        fields = ['title', 'description', 'html_file', 'thumbnail', 'points_reward', 'status', 'is_active', 'order', 'allowed_age_groups']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
            'html_file': forms.FileInput(attrs={'class': 'form-control'}),
            'thumbnail': forms.FileInput(attrs={'class': 'form-control'}),
            'points_reward': forms.NumberInput(attrs={'class': 'form-control'}),
            'status': forms.Select(attrs={'class': 'form-control'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'order': forms.NumberInput(attrs={'class': 'form-control'}),
            'allowed_age_groups': forms.SelectMultiple(attrs={'class': 'form-control'}),
        }
        labels = {
            'title': 'عنوان بازی',
            'description': 'توضیحات بازی',
            'html_file': 'فایل HTML بازی',
            'thumbnail': 'تصویر بازی',
            'points_reward': 'امتیاز جایزه',
            'status': 'وضعیت',
            'is_active': 'فعال',
            'order': 'ترتیب نمایش',
            'allowed_age_groups': 'گروه های سنی مجاز',
        }

class ChatRoomForm(forms.ModelForm):
    class Meta:
        model = ChatRoom
        fields = ['name', 'description', 'room_type']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'نام گروه'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'توضیحات (اختیاری)'}),
            'room_type': forms.Select(attrs={'class': 'form-control'}),
        }
        labels = {
            'name': 'نام گروه',
            'description': 'توضیحات',
            'room_type': 'نوع اتاق',
        }

class ChatMessageForm(forms.ModelForm):
    class Meta:
        model = ChatMessage
        fields = ['content', 'image', 'file', 'audio', 'video', 'sticker']
        widgets = {
            'content': forms.Textarea(attrs={'class': 'message-input', 'rows': 1, 'placeholder': 'پیام خود را بنویسید...', 'id': 'message-input'}),
        }

class AddParticipantForm(forms.Form):
    phone = forms.CharField(
        max_length=11,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': '09xxxxxxxxx', 'maxlength': '11'}),
        label='شماره تلفن کاربر'
    )
    
    def clean_phone(self):
        phone = self.cleaned_data['phone']
        if not phone.startswith('09') or len(phone) != 11:
            raise forms.ValidationError('شماره تلفن باید با 09 شروع شود و 11 رقم باشد')
        return phone

class ProductForm(forms.ModelForm):
    class Meta:
        model = Product
        fields = [
            'name', 'description', 'short_description', 'category', 'price', 
            'discounted_price', 'main_image', 'stock_quantity', 'status', 
            'is_featured', 'is_active', 'order', 'allowed_age_groups'
        ]
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'نام محصول'
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control', 
                'rows': 4,
                'placeholder': 'توضیحات کامل محصول'
            }),
            'short_description': forms.Textarea(attrs={
                'class': 'form-control', 
                'rows': 2,
                'placeholder': 'توضیح مختصر محصول'
            }),
            'category': forms.Select(attrs={'class': 'form-control'}),
            'price': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '0',
                'placeholder': 'قیمت به تومان'
            }),
            'discounted_price': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '0',
                'placeholder': 'قیمت تخفیف خورده'
            }),
            'main_image': forms.FileInput(attrs={'class': 'form-control'}),
            'stock_quantity': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '0',
                'placeholder': 'تعداد موجودی'
            }),
            'status': forms.Select(attrs={'class': 'form-control'}),
            'is_featured': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'order': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '0',
                'placeholder': 'ترتیب نمایش'
            }),
            'allowed_age_groups': forms.SelectMultiple(attrs={'class': 'form-control'}),
        }
        labels = {
            'name': 'نام محصول',
            'description': 'توضیحات کامل',
            'short_description': 'توضیح مختصر',
            'category': 'دسته بندی',
            'price': 'قیمت اصلی (تومان)',
            'discounted_price': 'قیمت تخفیف خورده (تومان)',
            'main_image': 'تصویر اصلی',
            'stock_quantity': 'تعداد موجودی',
            'status': 'وضعیت',
            'is_featured': 'محصول ویژه',
            'is_active': 'فعال',
            'order': 'ترتیب نمایش',
            'allowed_age_groups': 'گروه های سنی مجاز',
        }
    
    def clean(self):
        cleaned_data = super().clean()
        price = cleaned_data.get('price')
        discounted_price = cleaned_data.get('discounted_price')
        
        if discounted_price and price:
            if discounted_price >= price:
                raise forms.ValidationError('قیمت تخفیف خورده باید کمتر از قیمت اصلی باشد')
        
        return cleaned_data

class ProductCategoryForm(forms.ModelForm):
    class Meta:
        model = ProductCategory
        fields = ['name', 'description', 'image', 'is_active', 'order']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'نام دسته بندی'
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control', 
                'rows': 3,
                'placeholder': 'توضیحات دسته بندی'
            }),
            'image': forms.FileInput(attrs={'class': 'form-control'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'order': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '0',
                'placeholder': 'ترتیب نمایش'
            }),
        }
        labels = {
            'name': 'نام دسته بندی',
            'description': 'توضیحات',
            'image': 'تصویر دسته بندی',
            'is_active': 'فعال',
            'order': 'ترتیب نمایش',
        }

class ProductReviewForm(forms.ModelForm):
    class Meta:
        model = ProductReview
        fields = ['rating', 'comment']
        widgets = {
            'rating': forms.RadioSelect(
                choices=ProductReview.RATING_CHOICES, 
                attrs={'class': 'form-check-input'}
            ),
            'comment': forms.Textarea(attrs={
                'class': 'form-control', 
                'rows': 4, 
                'placeholder': 'نظر خود را درباره این محصول بنویسید...'
            }),
        }
        labels = {
            'rating': 'امتیاز شما',
            'comment': 'نظر شما',
        }

class CheckoutForm(forms.Form):
    customer_name = forms.CharField(
        max_length=100,
        widget=forms.TextInput(attrs={
            'class': 'form-control', 
            'placeholder': 'نام و نام خانوادگی'
        }),
        label='نام و نام خانوادگی'
    )
    customer_phone = forms.CharField(
        max_length=11,
        validators=[RegexValidator(
            regex=r'^09\d{9}$', 
            message="شماره موبایل باید با 09 شروع شود و 11 رقم باشد"
        )],
        widget=forms.TextInput(attrs={
            'class': 'form-control', 
            'placeholder': '09xxxxxxxxx', 
            'maxlength': '11'
        }),
        label='شماره تلفن'
    )
    customer_address = forms.CharField(
        widget=forms.Textarea(attrs={
            'class': 'form-control', 
            'rows': 3, 
            'placeholder': 'آدرس کامل پستی'
        }),
        label='آدرس'
    )
    customer_postal_code = forms.CharField(
        max_length=10,
        widget=forms.TextInput(attrs={
            'class': 'form-control', 
            'placeholder': 'کد پستی 10 رقمی', 
            'maxlength': '10'
        }),
        label='کد پستی'
    )
    payment_method = forms.ChoiceField(
        choices=Order.PAYMENT_METHODS,
        initial='card_to_card',
        widget=forms.RadioSelect(attrs={'class': 'form-check-input'}),
        label='روش پرداخت'
    )
    
    def clean_customer_postal_code(self):
        postal_code = self.cleaned_data['customer_postal_code']
        if not postal_code.isdigit() or len(postal_code) != 10:
            raise forms.ValidationError('کد پستی باید 10 رقم باشد')
        return postal_code

class PaymentReceiptForm(forms.ModelForm):
    class Meta:
        model = Order
        fields = ['payment_receipt']
        widgets = {
            'payment_receipt': forms.FileInput(attrs={'class': 'form-control'}),
        }
        labels = {
            'payment_receipt': 'عکس رسید پرداخت',
        }

class AddToCartForm(forms.Form):
    quantity = forms.IntegerField(
        min_value=1,
        initial=1,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'min': '1'
        }),
        label='تعداد'
    )

class ProductSearchForm(forms.Form):
    q = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'جستجو در محصولات...'
        }),
        label='جستجو'
    )
    category = forms.ModelChoiceField(
        queryset=ProductCategory.objects.filter(is_active=True),
        required=False,
        empty_label="همه دسته بندی ها",
        widget=forms.Select(attrs={'class': 'form-control'}),
        label='دسته بندی'
    )
    sort = forms.ChoiceField(
        choices=[
            ('newest', 'جدیدترین'),
            ('price_low', 'ارزان ترین'),
            ('price_high', 'گران ترین'),
            ('name', 'بر اساس نام'),
        ],
        required=False,
        initial='newest',
        widget=forms.Select(attrs={'class': 'form-control'}),
        label='مرتب سازی'
    )

class SocialProfileForm(forms.ModelForm):
    class Meta:
        model = SocialProfile
        fields = ['bio', 'website', 'is_private']
        widgets = {
            'bio': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'درباره خودت بنویس...'}),
            'website': forms.URLInput(attrs={'class': 'form-control', 'placeholder': 'https://...'}),
            'is_private': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
        labels = {
            'bio': 'بیوگرافی',
            'website': 'وبسایت',
            'is_private': 'حساب خصوصی',
        }

class PostForm(forms.ModelForm):
    class Meta:
        model = Post
        fields = ['caption', 'image', 'video', 'audio', 'location', 'content_type']
        widgets = {
            'caption': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'چه خبر؟...'}),
            'image': forms.FileInput(attrs={'class': 'form-control', 'accept': 'image/*'}),
            'video': forms.FileInput(attrs={'class': 'form-control', 'accept': 'video/*'}),
            'audio': forms.FileInput(attrs={'class': 'form-control', 'accept': 'audio/*'}),
            'location': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'مکان'}),
            'content_type': forms.HiddenInput(),
        }
        labels = {
            'caption': 'کپشن',
            'image': 'عکس',
            'video': 'ویدیو',
            'audio': 'صوت',
            'location': 'مکان',
        }

class StoryForm(forms.ModelForm):
    class Meta:
        model = Story
        fields = ['image', 'video', 'caption']
        widgets = {
            'caption': forms.Textarea(attrs={'class': 'form-control', 'rows': 2, 'placeholder': 'کپشن استوری...'}),
            'image': forms.FileInput(attrs={'class': 'form-control', 'accept': 'image/*'}),
            'video': forms.FileInput(attrs={'class': 'form-control', 'accept': 'video/*'}),
        }
        labels = {
            'caption': 'کپشن',
            'image': 'عکس',
            'video': 'ویدیو',
        }

class CommentForm(forms.ModelForm):
    class Meta:
        model = Comment
        fields = ['text']
        widgets = {
            'text': forms.Textarea(attrs={'class': 'form-control', 'rows': 2, 'placeholder': 'نظر خود را بنویسید...'}),
        }
        labels = {
            'text': 'نظر',
        }

class BookCategoryForm(forms.ModelForm):
    class Meta:
        model = BookCategory
        fields = ['name', 'description', 'is_active', 'order']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'order': forms.NumberInput(attrs={'class': 'form-control'}),
        }
        labels = {
            'name': 'نام دسته بندی',
            'description': 'توضیحات',
            'is_active': 'فعال',
            'order': 'ترتیب نمایش',
        }

class BookForm(forms.ModelForm):
    class Meta:
        model = Book
        fields = [
            'title', 'author', 'description', 'short_description', 'category',
            'book_type', 'pdf_file', 'cover_image', 'audio_files',
            'price', 'pages', 'publisher', 'isbn', 'publish_year',
            'status', 'is_featured', 'is_active', 'order'
        ]
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control'}),
            'author': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
            'short_description': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'category': forms.Select(attrs={'class': 'form-control'}),
            'book_type': forms.Select(attrs={'class': 'form-control'}),
            'price': forms.NumberInput(attrs={'class': 'form-control'}),
            'pages': forms.NumberInput(attrs={'class': 'form-control'}),
            'publisher': forms.TextInput(attrs={'class': 'form-control'}),
            'isbn': forms.TextInput(attrs={'class': 'form-control'}),
            'publish_year': forms.NumberInput(attrs={'class': 'form-control'}),
            'status': forms.Select(attrs={'class': 'form-control'}),
            'is_featured': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'order': forms.NumberInput(attrs={'class': 'form-control'}),
        }
        labels = {
            'title': 'عنوان کتاب',
            'author': 'نویسنده',
            'description': 'توضیحات کامل',
            'short_description': 'توضیح مختصر',
            'category': 'دسته بندی',
            'book_type': 'نوع کتاب',
            'pdf_file': 'فایل PDF',
            'cover_image': 'تصویر جلد',
            'audio_files': 'فایل های صوتی (اختیاری)',
            'price': 'قیمت (تومان)',
            'pages': 'تعداد صفحات',
            'publisher': 'ناشر',
            'isbn': 'شابک',
            'publish_year': 'سال انتشار',
            'status': 'وضعیت',
            'is_featured': 'کتاب ویژه',
            'is_active': 'فعال',
            'order': 'ترتیب نمایش',
        }

# فرم های تور مجازی
class VirtualTourCategoryForm(forms.ModelForm):
    class Meta:
        model = VirtualTourCategory
        fields = ['name', 'description', 'icon', 'color', 'order', 'is_active']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'نام دسته بندی'
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control', 
                'rows': 3,
                'placeholder': 'توضیحات دسته بندی'
            }),
            'icon': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'نام آیکون (مانند: fa-home)'
            }),
            'color': forms.TextInput(attrs={
                'class': 'form-control',
                'type': 'color'
            }),
            'order': forms.NumberInput(attrs={'class': 'form-control'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
        labels = {
            'name': 'نام دسته بندی',
            'description': 'توضیحات',
            'icon': 'آیکون',
            'color': 'رنگ',
            'order': 'ترتیب نمایش',
            'is_active': 'فعال',
        }

class VirtualTourForm(forms.ModelForm):
    class Meta:
        model = VirtualTour
        fields = [
            'title', 'description', 'category', 'embed_url', 'thumbnail', 
            'duration', 'location', 'tags', 'order', 'status', 'is_featured', 'is_active'
        ]
        widgets = {
            'title': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'عنوان تور مجازی'
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control', 
                'rows': 3,
                'placeholder': 'توضیحات تور مجازی'
            }),
            'category': forms.Select(attrs={'class': 'form-control'}),
            'embed_url': forms.URLInput(attrs={
                'class': 'form-control',
                'placeholder': 'https://example.com/your-virtual-tour'
            }),
            'thumbnail': forms.FileInput(attrs={'class': 'form-control'}),
            'duration': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'مانند: 30 دقیقه'
            }),
            'location': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'مکان تور'
            }),
            'tags': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'برچسب ها (با کاما جدا کنید)'
            }),
            'order': forms.NumberInput(attrs={'class': 'form-control'}),
            'status': forms.Select(attrs={'class': 'form-control'}),
            'is_featured': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
        labels = {
            'title': 'عنوان تور',
            'description': 'توضیحات',
            'category': 'دسته بندی',
            'embed_url': 'آدرس URL تور',
            'thumbnail': 'تصویر بندانگشتی',
            'duration': 'مدت زمان',
            'location': 'مکان',
            'tags': 'برچسب ها',
            'order': 'ترتیب نمایش',
            'status': 'وضعیت',
            'is_featured': 'تور ویژه',
            'is_active': 'فعال',
        }

# اضافه کردن به انتهای فایل forms.py

class CharityCategoryForm(forms.ModelForm):
    class Meta:
        model = CharityCategory
        fields = ['name', 'description', 'icon', 'color', 'image', 'is_active', 'order']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'نام دسته‌بندی'
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control', 
                'rows': 3,
                'placeholder': 'توضیحات دسته‌بندی'
            }),
            'icon': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'نام آیکون (مانند: fa-heart)'
            }),
            'color': forms.TextInput(attrs={
                'class': 'form-control',
                'type': 'color'
            }),
            'image': forms.FileInput(attrs={'class': 'form-control'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'order': forms.NumberInput(attrs={'class': 'form-control'}),
        }
        labels = {
            'name': 'نام دسته‌بندی',
            'description': 'توضیحات',
            'icon': 'آیکون',
            'color': 'رنگ',
            'image': 'تصویر',
            'is_active': 'فعال',
            'order': 'ترتیب نمایش',
        }

class CharityProjectForm(forms.ModelForm):
    class Meta:
        model = CharityProject
        fields = [
            'title', 'description', 'short_description', 'category', 
            'target_amount', 'start_date', 'end_date', 'location', 
            'beneficiary_count', 'main_image', 'status', 'is_featured', 
            'is_urgent', 'is_active', 'card_number', 'card_holder', 'bank_name'
        ]
        widgets = {
            'title': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'عنوان پروژه خیریه'
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control', 
                'rows': 5,
                'placeholder': 'توضیحات کامل پروژه'
            }),
            'short_description': forms.Textarea(attrs={
                'class': 'form-control', 
                'rows': 3,
                'placeholder': 'توضیح مختصر پروژه'
            }),
            'category': forms.Select(attrs={'class': 'form-control'}),
            'target_amount': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '1000',
                'placeholder': 'مبلغ هدف به تومان'
            }),
            'start_date': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'
            }),
            'end_date': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'
            }),
            'location': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'مکان اجرای پروژه'
            }),
            'beneficiary_count': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '0',
                'placeholder': 'تعداد بهره‌برداران'
            }),
            'main_image': forms.FileInput(attrs={'class': 'form-control'}),
            'status': forms.Select(attrs={'class': 'form-control'}),
            'is_featured': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'is_urgent': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'card_number': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'شماره کارت ۱۶ رقمی',
                'maxlength': '16'
            }),
            'card_holder': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'نام صاحب کارت'
            }),
            'bank_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'نام بانک'
            }),
        }
        labels = {
            'title': 'عنوان پروژه',
            'description': 'توضیحات کامل',
            'short_description': 'توضیح مختصر',
            'category': 'دسته‌بندی',
            'target_amount': 'مبلغ هدف (تومان)',
            'start_date': 'تاریخ شروع',
            'end_date': 'تاریخ پایان (اختیاری)',
            'location': 'مکان اجرا',
            'beneficiary_count': 'تعداد بهره‌برداران',
            'main_image': 'تصویر اصلی',
            'status': 'وضعیت',
            'is_featured': 'پروژه ویژه',
            'is_urgent': 'پروژه فوری',
            'is_active': 'فعال',
            'card_number': 'شماره کارت',
            'card_holder': 'صاحب کارت',
            'bank_name': 'نام بانک',
        }
    
    def clean_card_number(self):
        card_number = self.cleaned_data['card_number']
        if not card_number.isdigit() or len(card_number) != 16:
            raise forms.ValidationError('شماره کارت باید ۱۶ رقم باشد')
        return card_number

class CharityDonationForm(forms.ModelForm):
    custom_amount = forms.DecimalField(
        required=False,
        max_digits=12,
        decimal_places=0,
        min_value=1000,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'placeholder': 'مبلغ دلخواه (تومان)',
            'min': '1000'
        }),
        label='مبلغ دلخواه'
    )
    
    class Meta:
        model = CharityDonation
        fields = ['amount', 'is_anonymous', 'message']
        widgets = {
            'amount': forms.NumberInput(attrs={
                'class': 'form-control donation-amount',
                'min': '1000'
            }),
            'is_anonymous': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'message': forms.Textarea(attrs={
                'class': 'form-control', 
                'rows': 3,
                'placeholder': 'پیام خود را برای خیریه بنویسید...'
            }),
        }
        labels = {
            'amount': 'مبلغ کمک (تومان)',
            'is_anonymous': 'کمک ناشناس',
            'message': 'پیام شما',
        }
    
    def clean(self):
        cleaned_data = super().clean()
        amount = cleaned_data.get('amount')
        custom_amount = cleaned_data.get('custom_amount')
        
        if custom_amount:
            cleaned_data['amount'] = custom_amount
        elif not amount:
            raise forms.ValidationError('لطفاً مبلغ کمک را انتخاب یا وارد کنید')
        
        return cleaned_data

class CharityPaymentForm(forms.ModelForm):
    class Meta:
        model = CharityDonation
        fields = ['payment_receipt']
        widgets = {
            'payment_receipt': forms.FileInput(attrs={'class': 'form-control'}),
        }
        labels = {
            'payment_receipt': 'عکس رسید پرداخت',
        }

class CharityUpdateForm(forms.ModelForm):
    class Meta:
        model = CharityUpdate
        fields = ['title', 'content', 'update_type', 'image', 'video', 'spent_amount', 'expense_description']
        widgets = {
            'title': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'عنوان به‌روزرسانی'
            }),
            'content': forms.Textarea(attrs={
                'class': 'form-control', 
                'rows': 6,
                'placeholder': 'متن به‌روزرسانی...'
            }),
            'update_type': forms.Select(attrs={'class': 'form-control'}),
            'image': forms.FileInput(attrs={'class': 'form-control'}),
            'video': forms.FileInput(attrs={'class': 'form-control'}),
            'spent_amount': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '0',
                'placeholder': 'مبلغ هزینه شده'
            }),
            'expense_description': forms.Textarea(attrs={
                'class': 'form-control', 
                'rows': 3,
                'placeholder': 'توضیحات هزینه...'
            }),
        }
        labels = {
            'title': 'عنوان',
            'content': 'محتوا',
            'update_type': 'نوع به‌روزرسانی',
            'image': 'تصویر',
            'video': 'ویدیو',
            'spent_amount': 'مبلغ هزینه شده (تومان)',
            'expense_description': 'توضیحات هزینه',
        }

class CharityVolunteerForm(forms.ModelForm):
    class Meta:
        model = CharityVolunteer
        fields = ['motivation', 'skills', 'available_hours']
        widgets = {
            'motivation': forms.Textarea(attrs={
                'class': 'form-control', 
                'rows': 4,
                'placeholder': 'انگیزه خود را برای همکاری در این پروژه بنویسید...'
            }),
            'skills': forms.Textarea(attrs={
                'class': 'form-control', 
                'rows': 3,
                'placeholder': 'مهارت‌ها و تخصص‌های خود را بنویسید...'
            }),
            'available_hours': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '1',
                'max': '40',
                'placeholder': 'ساعات در هفته'
            }),
        }
        labels = {
            'motivation': 'انگیزه همکاری',
            'skills': 'مهارت‌ها',
            'available_hours': 'ساعات قابل اختصاص در هفته',
        }