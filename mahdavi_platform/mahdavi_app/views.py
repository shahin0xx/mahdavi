from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth import login, logout, authenticate, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse, HttpResponse, FileResponse
from django.utils import timezone
from django.db.models import Q, Count, Sum, Avg
from django.db import models, transaction
from django.core.files.storage import FileSystemStorage
from django.views import View
from django.views.generic import TemplateView
from django.core.mail import send_mail
from django.conf import settings
from django.core.paginator import Paginator
from .models import *
from .forms import *
import traceback
import json

def home(request):
    try:
        user_age_group = None
        age_group_settings = None
        
        if request.user.is_authenticated:
            user_age_group = request.user.age_group
            age_group_settings = AgeGroupSettings.objects.filter(
                age_group=user_age_group, 
                is_active=True
            ).first()
        
        return render(request, 'home.html', {
            'user_age_group': user_age_group,
            'age_group_settings': age_group_settings,
        })
    except Exception as e:
        messages.error(request, f'خطا در بارگذاری صفحه اصلی: {str(e)}')
        return render(request, 'home.html', {})

class EmailService:
    @staticmethod
    def send_verification_email(user_email, verification_code):
        try:
            send_mail(
                'کد تایید ایمیل - پلتفرم مهدوی',
                f"""
                سلام
                
                کد تایید ایمیل شما:
                {verification_code}
                
                این کد برای 10 دقیقه معتبر است.
                
                با تشکر
                پلتفرم مهدوی
                """,
                settings.DEFAULT_FROM_EMAIL,
                [user_email],
                fail_silently=False,
            )
            return True
        except Exception as e:
            print(f"خطا در ارسال ایمیل: {e}")
            return False
    
    @staticmethod
    def send_password_reset_email(user_email, reset_code):
        try:
            send_mail(
                'بازیابی رمز عبور - پلتفرم مهدوی',
                f"""
                سلام
                
                کد بازیابی رمز عبور شما:
                {reset_code}
                
                این کد برای 10 دقیقه معتبر است.
                
                اگر شما این درخواست را نکرده‌اید، لطفاً این ایمیل را نادیده بگیرید.
                
                با تشکر
                پلتفرم مهدوی
                """,
                settings.DEFAULT_FROM_EMAIL,
                [user_email],
                fail_silently=False,
            )
            return True
        except Exception as e:
            print(f"خطا در ارسال ایمیل: {e}")
            return False

def user_register(request):
    try:
        if request.method == 'POST':
            form = RegisterForm(request.POST)
            
            if form.is_valid():
                first_name = form.cleaned_data['first_name']
                last_name = form.cleaned_data['last_name']
                phone = form.cleaned_data['phone']
                email = form.cleaned_data['email']
                age = form.cleaned_data['age']
                password = form.cleaned_data['password']
                
                if CustomUser.objects.filter(email=email).exists():
                    messages.error(request, 'این ایمیل قبلاً ثبت شده است')
                    return render(request, 'register.html', {'form': form})
                
                if CustomUser.objects.filter(phone=phone).exists():
                    messages.error(request, 'این شماره تلفن قبلاً ثبت شده است')
                    return render(request, 'register.html', {'form': form})
                
                user = CustomUser.objects.create_user(
                    first_name=first_name,
                    last_name=last_name,
                    phone=phone,
                    email=email,
                    age=age,
                    password=password
                )
                
                verification_code = user.generate_verification_code()
                user.email_verification_code = verification_code
                user.verification_code_sent_at = timezone.now()
                user.save()
                
                print("=" * 60)
                print("🎯 کد تایید ایمیل برای کاربر جدید:")
                print(f"📧 ایمیل: {email}")
                print(f"🔑 کد تایید: {verification_code}")
                print("=" * 60)
                
                email_sent = EmailService.send_verification_email(email, verification_code)
                
                if email_sent:
                    messages.success(request, 'کد تایید به ایمیل شما ارسال شد')
                else:
                    messages.warning(request, 'خطا در ارسال ایمیل، اما می‌توانید از کد زیر استفاده کنید')
                
                messages.info(request, f'کد تایید: {verification_code}')
                
                request.session['pending_user_id'] = user.id
                request.session['pending_user_email'] = email
                return redirect('verify_email')
            else:
                messages.error(request, 'لطفاً اطلاعات را به درستی وارد کنید')
        else:
            form = RegisterForm()
        
        user_age_group = request.user.age_group if request.user.is_authenticated else None
        age_group_settings = AgeGroupSettings.objects.filter(
            age_group=user_age_group, is_active=True
        ).first() if user_age_group else None
        
        return render(request, 'register.html', {
            'form': form,
            'user_age_group': user_age_group,
            'age_group_settings': age_group_settings,
        })
    except Exception as e:
        messages.error(request, f'خطا در پردازش درخواست ثبت نام: {str(e)}')
        return render(request, 'register.html', {'form': RegisterForm()})

def verify_email(request):
    try:
        pending_user_id = request.session.get('pending_user_id')
        pending_user_email = request.session.get('pending_user_email')
        
        if not pending_user_id or not pending_user_email:
            messages.error(request, 'دسترسی نامعتبر')
            return render(request, 'verify_email.html', {'form': EmailVerificationForm()})
        
        user = CustomUser.objects.filter(id=pending_user_id, email=pending_user_email).first()
        if not user:
            messages.error(request, 'کاربر یافت نشد')
            return render(request, 'verify_email.html', {'form': EmailVerificationForm()})
        
        if request.method == 'POST':
            form = EmailVerificationForm(request.POST)
            if form.is_valid():
                entered_code = form.cleaned_data['verification_code']
                
                time_difference = timezone.now() - user.verification_code_sent_at
                if time_difference.total_seconds() > 600:
                    messages.error(request, 'کد تایید منقضی شده است. لطفاً مجدداً درخواست کنید.')
                    return render(request, 'verify_email.html', {'form': form, 'email': pending_user_email})
                
                if entered_code == user.email_verification_code:
                    user.email_verified = True
                    user.email_verification_code = ''
                    user.save()
                    
                    del request.session['pending_user_id']
                    del request.session['pending_user_email']
                    
                    login(request, user)
                    messages.success(request, f'حساب کاربری با موفقیت فعال شد! خوش آمدید {user.get_full_name()}!')
                    return redirect('dashboard')
                else:
                    messages.error(request, 'کد تایید نامعتبر است')
        else:
            form = EmailVerificationForm()
        
        return render(request, 'verify_email.html', {
            'form': form,
            'email': pending_user_email,
        })
    except Exception as e:
        messages.error(request, f'خطا در تایید ایمیل: {str(e)}')
        return render(request, 'verify_email.html', {'form': EmailVerificationForm()})

def resend_verification_code(request):
    try:
        pending_user_id = request.session.get('pending_user_id')
        pending_user_email = request.session.get('pending_user_email')
        
        if not pending_user_id or not pending_user_email:
            messages.error(request, 'دسترسی نامعتبر')
            return redirect('verify_email')
        
        user = CustomUser.objects.filter(id=pending_user_id, email=pending_user_email).first()
        if not user:
            messages.error(request, 'کاربر یافت نشد')
            return redirect('verify_email')
        
        new_verification_code = user.generate_verification_code()
        user.email_verification_code = new_verification_code
        user.verification_code_sent_at = timezone.now()
        user.save()
        
        print("=" * 60)
        print("🔄 کد تایید جدید:")
        print(f"📧 ایمیل: {pending_user_email}")
        print(f"🔑 کد تایید جدید: {new_verification_code}")
        print("=" * 60)
        
        email_sent = EmailService.send_verification_email(pending_user_email, new_verification_code)
        
        if email_sent:
            messages.success(request, 'کد تایید جدید برای شما ارسال شد')
        else:
            messages.warning(request, 'خطا در ارسال ایمیل، اما می‌توانید از کد زیر استفاده کنید')
        
        return redirect('verify_email')
    except Exception as e:
        messages.error(request, f'خطا در ارسال مجدد کد تایید: {str(e)}')
        return redirect('verify_email')

def forgot_password(request):
    try:
        if request.method == 'POST':
            form = ForgotPasswordForm(request.POST)
            if form.is_valid():
                email = form.cleaned_data['email']
                
                user = CustomUser.objects.filter(email=email, is_active=True).first()
                if user:
                    reset_code = user.generate_reset_code()
                    user.reset_password_code = reset_code
                    user.reset_code_sent_at = timezone.now()
                    user.save()
                    
                    if EmailService.send_password_reset_email(email, reset_code):
                        messages.success(request, 'ایمیل بازیابی رمز عبور برای شما ارسال شد')
                        request.session['reset_password_email'] = email
                        return redirect('reset_password')
                    else:
                        messages.error(request, 'خطا در ارسال ایمیل. لطفاً مجدداً تلاش کنید.')
                else:
                    messages.error(request, 'کاربری با این ایمیل یافت نشد')
        else:
            form = ForgotPasswordForm()
        
        user_age_group = request.user.age_group if request.user.is_authenticated else None
        age_group_settings = AgeGroupSettings.objects.filter(
            age_group=user_age_group, is_active=True
        ).first() if user_age_group else None
        
        return render(request, 'forgot_password.html', {
            'form': form,
            'user_age_group': user_age_group,
            'age_group_settings': age_group_settings,
        })
    except Exception as e:
        messages.error(request, f'خطا در پردازش بازیابی رمز عبور: {str(e)}')
        return render(request, 'forgot_password.html', {'form': ForgotPasswordForm()})

def reset_password(request):
    try:
        reset_email = request.session.get('reset_password_email')
        
        if not reset_email:
            messages.error(request, 'دسترسی نامعتبر')
            return render(request, 'reset_password.html', {'form': ResetPasswordForm()})
        
        user = CustomUser.objects.filter(email=reset_email, is_active=True).first()
        if not user:
            messages.error(request, 'کاربر یافت نشد')
            return render(request, 'reset_password.html', {'form': ResetPasswordForm()})
        
        if request.method == 'POST':
            form = ResetPasswordForm(request.POST)
            if form.is_valid():
                entered_code = form.cleaned_data['reset_code']
                new_password = form.cleaned_data['new_password']
                
                time_difference = timezone.now() - user.reset_code_sent_at
                if time_difference.total_seconds() > 600:
                    messages.error(request, 'کد بازیابی منقضی شده است. لطفاً مجدداً درخواست کنید.')
                    return render(request, 'reset_password.html', {'form': form})
                
                if entered_code == user.reset_password_code:
                    user.set_password(new_password)
                    user.reset_password_code = ''
                    user.save()
                    
                    del request.session['reset_password_email']
                    
                    messages.success(request, 'رمز عبور شما با موفقیت تغییر کرد. اکنون می‌توانید وارد شوید.')
                    return redirect('login')
                else:
                    messages.error(request, 'کد بازیابی نامعتبر است')
        else:
            form = ResetPasswordForm()
        
        return render(request, 'reset_password.html', {
            'form': form,
            'email': reset_email,
        })
    except Exception as e:
        messages.error(request, f'خطا در بازنشانی رمز عبور: {str(e)}')
        return render(request, 'reset_password.html', {'form': ResetPasswordForm()})

@login_required
def change_password(request):
    try:
        if request.method == 'POST':
            form = ChangePasswordForm(request.POST)
            if form.is_valid():
                current_password = form.cleaned_data['current_password']
                new_password = form.cleaned_data['new_password']
                
                if not request.user.check_password(current_password):
                    messages.error(request, 'رمز عبور فعلی نادرست است')
                    return render(request, 'change_password.html', {'form': form})
                
                request.user.set_password(new_password)
                request.user.save()
                update_session_auth_hash(request, request.user)
                
                messages.success(request, 'رمز عبور شما با موفقیت تغییر کرد')
                return redirect('profile')
        else:
            form = ChangePasswordForm()
        
        user_age_group = request.user.age_group
        age_group_settings = AgeGroupSettings.objects.filter(
            age_group=user_age_group, is_active=True
        ).first()
        
        return render(request, 'change_password.html', {
            'form': form,
            'user_age_group': user_age_group,
            'age_group_settings': age_group_settings,
        })
    except Exception as e:
        messages.error(request, f'خطا در تغییر رمز عبور: {str(e)}')
        return render(request, 'change_password.html', {'form': ChangePasswordForm()})

def index(request):
    try:
        user_age_group = request.user.age_group if request.user.is_authenticated else None
        
        stations = Station.objects.filter(is_active=True)
        if user_age_group:
            stations = stations.filter(allowed_age_groups__contains=user_age_group)
        stations = stations.order_by('order')
        
        station_id = request.GET.get('station')
        if station_id:
            current_station = Station.objects.filter(id=station_id, is_active=True).first()
            if not current_station:
                current_station = stations.first()
        else:
            current_station = stations.first()
        
        if not current_station:
            return render(request, 'index.html', {})
        
        prev_station = Station.objects.filter(
            order__lt=current_station.order, is_active=True
        ).order_by('-order').first()
        
        next_station = Station.objects.filter(
            order__gt=current_station.order, is_active=True
        ).order_by('order').first()
        
        user_progress_percentage = 0
        completed_contents = 0
        total_contents = current_station.get_active_contents_count()
        
        if request.user.is_authenticated:
            user_progress_data = UserProgress.objects.filter(
                user=request.user, station=current_station
            ).first()
            
            if user_progress_data:
                completed_contents = sum([
                    user_progress_data.completed_story,
                    user_progress_data.completed_prayer,
                    user_progress_data.completed_article,
                    user_progress_data.completed_video,
                    user_progress_data.completed_quiz
                ])
                user_progress_percentage = (completed_contents / total_contents * 100) if total_contents > 0 else 0
        
        age_group_settings = AgeGroupSettings.objects.filter(
            age_group=user_age_group, is_active=True
        ).first() if user_age_group else None
        
        return render(request, 'index.html', {
            'stations': stations,
            'current_station': current_station,
            'prev_station': prev_station,
            'next_station': next_station,
            'total_stations': stations.count(),
            'all_stations': stations,
            'user_progress_percentage': int(user_progress_percentage),
            'completed_contents': completed_contents,
            'total_contents': total_contents,
            'user_age_group': user_age_group,
            'age_group_settings': age_group_settings,
        })
    except Exception as e:
        messages.error(request, f'خطا در بارگذاری صفحه اصلی: {str(e)}')
        return render(request, 'index.html', {})

def user_login(request):
    try:
        if request.method == 'POST':
            form = LoginForm(request.POST)
            if form.is_valid():
                phone = form.cleaned_data['phone']
                password = form.cleaned_data['password']
                user = authenticate(request, phone=phone, password=password)
                
                if user:
                    if user.email_verified:
                        login(request, user)
                        messages.success(request, f'خوش آمدید {user.get_full_name()}!')
                        return redirect('dashboard')
                    else:
                        messages.error(request, 'لطفاً ابتدا ایمیل خود را تایید کنید')
                        request.session['pending_user_id'] = user.id
                        request.session['pending_user_email'] = user.email
                        return redirect('verify_email')
                else:
                    messages.error(request, 'شماره موبایل یا رمز عبور اشتباه است')
        else:
            form = LoginForm()
        
        return render(request, 'login.html', {'form': form})
    except Exception as e:
        messages.error(request, f'خطا در ورود به سیستم: {str(e)}')
        return render(request, 'login.html', {'form': LoginForm()})

@login_required
def dashboard(request):
    try:
        user = request.user
        user_age_group = user.age_group
        
        stations = Station.objects.filter(is_active=True)
        if user_age_group:
            stations = stations.filter(allowed_age_groups__contains=user_age_group)
        
        station_progress = []
        for station in stations:
            progress, created = UserProgress.objects.get_or_create(user=user, station=station)
            
            completed_count = sum([
                progress.completed_story,
                progress.completed_prayer,
                progress.completed_article,
                progress.completed_video,
                progress.completed_quiz
            ])
            total_count = 5
            
            station_progress.append({
                'station': station,
                'completed': completed_count,
                'total': total_count,
                'percentage': (completed_count / total_count) * 100 if total_count > 0 else 0,
                'is_accessible': user.points >= station.points_required
            })
        
        spiritual_grade = calculate_spiritual_grade(user)
        badges = UserBadge.objects.filter(user=user)
        total_stations = stations.count()
        
        completed_stations = UserProgress.objects.filter(user=user).exclude(
            Q(completed_story=False) & Q(completed_prayer=False) & 
            Q(completed_article=False) & Q(completed_video=False) & Q(completed_quiz=False)
        ).count()
        
        age_group_settings = AgeGroupSettings.objects.filter(
            age_group=user_age_group, is_active=True
        ).first()
        
        return render(request, 'dashboard.html', {
            'user': user,
            'station_progress': station_progress,
            'spiritual_grade': spiritual_grade,
            'badges': badges,
            'completed_stations': completed_stations,
            'total_stations': total_stations,
            'user_age_group': user_age_group,
            'age_group_settings': age_group_settings,
        })
    except Exception as e:
        messages.error(request, f'خطا در بارگذاری داشبورد: {str(e)}')
        return render(request, 'dashboard.html', {})

@login_required
def profile(request):
    try:
        if request.method == 'POST':
            form = ProfileForm(request.POST, request.FILES, instance=request.user)
            if form.is_valid():
                form.save()
                messages.success(request, 'پروفایل با موفقیت به‌روزرسانی شد')
                return redirect('profile')
        else:
            form = ProfileForm(instance=request.user)
        
        user = request.user
        user_age_group = user.age_group
        
        stations = Station.objects.filter(is_active=True)
        if user_age_group:
            stations = stations.filter(allowed_age_groups__contains=user_age_group)
        
        total_stations = stations.count()
        completed_stations = UserProgress.objects.filter(user=user).exclude(
            Q(completed_story=False) & Q(completed_prayer=False) & 
            Q(completed_article=False) & Q(completed_video=False) & Q(completed_quiz=False)
        ).count()
        
        total_contents = total_stations * 5
        user_progress = UserProgress.objects.filter(user=user)
        completed_contents = 0
        for progress in user_progress:
            completed_contents += sum([
                progress.completed_story,
                progress.completed_prayer,
                progress.completed_article,
                progress.completed_video,
                progress.completed_quiz
            ])
        
        progress_percentage = (completed_contents / total_contents * 100) if total_contents > 0 else 0
        
        achievements = [
            {
                'name': 'عارف مهدوی',
                'description': 'کامل کردن ۸۰٪ ایستگاه‌ها',
                'icon': '🌟',
                'earned': completed_stations >= total_stations * 0.8,
                'remaining': f'{max(0, int(total_stations * 0.8) - completed_stations)} ایستگاه'
            },
            {
                'name': 'دعاخوان',
                'description': 'خواندن ۱۰ دعا',
                'icon': '🙏',
                'earned': user_progress.filter(completed_prayer=True).count() >= 10,
                'remaining': f'{max(0, 10 - user_progress.filter(completed_prayer=True).count())} دعا'
            },
            {
                'name': 'یاور مهدوی',
                'description': 'کسب ۵۰۰ امتیاز',
                'icon': '💫',
                'earned': user.points >= 500,
                'remaining': f'{max(0, 500 - user.points)} امتیاز'
            }
        ]
        
        age_group_settings = AgeGroupSettings.objects.filter(
            age_group=user_age_group, is_active=True
        ).first()
        
        return render(request, 'profile.html', {
            'form': form,
            'user': user,
            'completed_stations': completed_stations,
            'total_stations': total_stations,
            'progress_percentage': int(progress_percentage),
            'achievements': achievements,
            'badges_count': UserBadge.objects.filter(user=user).count(),
            'user_age_group': user_age_group,
            'age_group_settings': age_group_settings,
        })
    except Exception as e:
        messages.error(request, f'خطا در بارگذاری پروفایل: {str(e)}')
        return render(request, 'profile.html', {'form': ProfileForm(instance=request.user)})

def user_logout(request):
    try:
        logout(request)
        messages.success(request, 'با موفقیت خارج شدید')
        return redirect('index')
    except Exception as e:
        messages.error(request, f'خطا در خروج از سیستم: {str(e)}')
        return redirect('index')

@login_required
def station_detail(request, station_id):
    try:
        station = get_object_or_404(Station, id=station_id)
        user_age_group = request.user.age_group
        
        if not station.is_allowed_for_age_group(user_age_group):
            messages.error(request, 'شما دسترسی به این ایستگاه را ندارید')
            return redirect('index')
        
        if request.user.points < station.points_required:
            messages.error(request, 'امتیاز شما برای دسترسی به این ایستگاه کافی نیست')
            return redirect('index')
        
        user_progress, created = UserProgress.objects.get_or_create(
            user=request.user, station=station
        )
        
        total_contents = station.get_active_contents_count()
        completed_count = 0
        
        if station.story_content and user_progress.completed_story:
            completed_count += 1
        if station.prayer_content and user_progress.completed_prayer:
            completed_count += 1
        if station.article_content and user_progress.completed_article:
            completed_count += 1
        if station.video_file and user_progress.completed_video:
            completed_count += 1
        if station.quiz_question and user_progress.completed_quiz:
            completed_count += 1
        
        progress_info = {
            'completed': completed_count,
            'total': total_contents,
            'percentage': (completed_count / total_contents * 100) if total_contents > 0 else 0,
            'station_completed': completed_count == total_contents and total_contents > 0
        }
        
        quiz_choices = []
        if station.quiz_question:
            choices = [
                (1, station.choice1),
                (2, station.choice2),
                (3, station.choice3),
                (4, station.choice4),
            ]
            quiz_choices = [(idx, choice) for idx, choice in choices if choice]
        
        quiz_form = QuizForm(choices=quiz_choices) if quiz_choices else None
        
        age_group_settings = AgeGroupSettings.objects.filter(
            age_group=user_age_group, is_active=True
        ).first()
        
        return render(request, 'station_detail.html', {
            'station': station,
            'progress': progress_info,
            'user_progress': user_progress,
            'quiz_form': quiz_form,
            'next_station': Station.objects.filter(order=station.order + 1, is_active=True).first(),
            'user_age_group': user_age_group,
            'age_group_settings': age_group_settings,
        })
    except Exception as e:
        messages.error(request, f'خطا در بارگذاری ایستگاه: {str(e)}')
        return redirect('index')
@login_required
def complete_content(request, station_id, content_type):
    try:
        if request.method != 'POST':
            return redirect('station_detail', station_id=station_id)
        
        station = get_object_or_404(Station, id=station_id)
        user_age_group = request.user.age_group
        
        if not station.is_allowed_for_age_group(user_age_group):
            messages.error(request, 'دسترسی غیرمجاز')
            return redirect('station_detail', station_id=station_id)
        
        if request.user.points < station.points_required:
            messages.error(request, 'دسترسی غیرمجاز')
            return redirect('station_detail', station_id=station_id)
        
        user_progress, created = UserProgress.objects.get_or_create(
            user=request.user, station=station
        )
        
        content_config = {
            'story': ('completed_story', station.story_points, 'داستان'),
            'prayer': ('completed_prayer', station.prayer_points, 'دعا'),
            'article': ('completed_article', station.article_points, 'مطلب'),
            'video': ('completed_video', station.video_points, 'ویدیو'),
        }
        
        if content_type not in content_config:
            messages.error(request, 'نوع محتوا نامعتبر است')
            return redirect('station_detail', station_id=station_id)
        
        field_name, points, content_name = content_config[content_type]
        
        if content_type == 'video' and not station.video_file:
            messages.info(request, 'ویدیویی برای این ایستگاه وجود ندارد')
            return redirect('station_detail', station_id=station_id)
        
        if getattr(user_progress, field_name):
            messages.info(request, 'این محتوا قبلاً تکمیل شده است')
            return redirect('station_detail', station_id=station_id)
        
        setattr(user_progress, field_name, True)
        user_progress.total_score += points
        user_progress.save()
        
        request.user.points += points
        request.user.save()
        
        check_level_up(request.user, request)
        check_badges(request.user, request)
        
        messages.success(request, f'{content_name} با موفقیت تکمیل شد! +{points} امتیاز')
        return redirect('station_detail', station_id=station_id)
        
    except Exception as e:
        messages.error(request, f'خطا در تکمیل محتوا: {str(e)}')
        return redirect('station_detail', station_id=station_id)

@login_required
def submit_quiz(request, station_id):
    try:
        if request.method != 'POST':
            return redirect('station_detail', station_id=station_id)
        
        station = get_object_or_404(Station, id=station_id)
        user_age_group = request.user.age_group
        
        if not station.is_allowed_for_age_group(user_age_group):
            messages.error(request, 'دسترسی غیرمجاز')
            return redirect('station_detail', station_id=station_id)
        
        if request.user.points < station.points_required:
            messages.error(request, 'دسترسی غیرمجاز')
            return redirect('station_detail', station_id=station_id)
        
        user_progress, created = UserProgress.objects.get_or_create(
            user=request.user, station=station
        )
        
        if user_progress.quiz_passed:
            messages.info(request, 'شما قبلاً این آزمون را با موفقیت گذرانده‌اید')
            return redirect('station_detail', station_id=station_id)
        
        if not station.quiz_question or not station.correct_choice:
            messages.error(request, 'آزمون برای این ایستگاه تنظیم نشده است')
            return redirect('station_detail', station_id=station_id)
        
        selected_choice = request.POST.get('selected_choice')
        if not selected_choice:
            messages.error(request, 'لطفاً یک گزینه را انتخاب کنید')
            return redirect('station_detail', station_id=station_id)
        
        try:
            selected_choice = int(selected_choice)
            is_correct = (selected_choice == station.correct_choice)
            
            user_progress.completed_quiz = True
            
            if is_correct:
                user_progress.quiz_passed = True
                user_progress.total_score += station.quiz_points
                user_progress.save()
                
                request.user.points += station.quiz_points
                request.user.save()
                
                check_level_up(request.user, request)
                check_badges(request.user, request)
                
                messages.success(request, f'✅ پاسخ شما صحیح است! آزمون با موفقیت گذرانده شد! +{station.quiz_points} امتیاز')
            else:
                user_progress.quiz_passed = False
                user_progress.save()
                messages.error(request, '❌ پاسخ شما صحیح نیست. لطفاً مجدداً تلاش کنید')
        except ValueError:
            messages.error(request, 'خطا در پردازش پاسخ')
        
        return redirect('station_detail', station_id=station_id)
        
    except Exception as e:
        messages.error(request, f'خطا در ثبت آزمون: {str(e)}')
        return redirect('station_detail', station_id=station_id)

def calculate_spiritual_grade(user):
    try:
        user_age_group = user.age_group
        
        stations = Station.objects.filter(is_active=True)
        if user_age_group:
            stations = stations.filter(allowed_age_groups__contains=user_age_group)
        
        total_stations = stations.count()
        completed_stations = UserProgress.objects.filter(user=user).exclude(
            Q(completed_story=False) & Q(completed_prayer=False) & 
            Q(completed_article=False) & Q(completed_video=False) & Q(completed_quiz=False)
        ).count()
        
        completion_percentage = (completed_stations / total_stations * 100) if total_stations > 0 else 0
        
        grades = [
            (90, 'A+', 'سفیر مهدوی', '#d4af37'),
            (70, 'A', 'یاور مهدوی', '#2c5aa0'),
            (50, 'B', 'عاشق مهدوی', '#3a7bd5'),
            (30, 'C', 'نوآموز مهدوی', '#666'),
        ]
        
        for threshold, grade, title, color in grades:
            if completion_percentage >= threshold:
                return {'grade': grade, 'title': title, 'color': color, 'percentage': completion_percentage}
        
        return {'grade': 'D', 'title': 'علاقه‌مند', 'color': '#999', 'percentage': completion_percentage}
    except:
        return {'grade': 'D', 'title': 'علاقه‌مند', 'color': '#999', 'percentage': 0}

def check_level_up(user, request):
    try:
        user_age_group = user.age_group
        
        stations = Station.objects.filter(is_active=True)
        if user_age_group:
            stations = stations.filter(allowed_age_groups__contains=user_age_group)
        
        total_stations = stations.count()
        completed_stations = UserProgress.objects.filter(user=user).exclude(
            Q(completed_story=False) & Q(completed_prayer=False) & 
            Q(completed_article=False) & Q(completed_video=False) & Q(completed_quiz=False)
        ).count()
        
        completion_percentage = (completed_stations / total_stations * 100) if total_stations > 0 else 0
        
        levels = [
            (90, 'ambassador', 'سفیر مهدوی'),
            (70, 'assistant', 'یاور مهدوی'),
            (50, 'lover', 'عاشق مهدوی'),
            (30, 'novice', 'نوآموز مهدوی'),
        ]
        
        for threshold, level_value, level_name in levels:
            if completion_percentage >= threshold and user.spiritual_level != level_value:
                user.spiritual_level = level_value
                user.save()
                messages.success(request, f'تبریک! شما به سطح {level_name} ارتقا یافتید!')
                break
    except Exception as e:
        print(f"خطا در بررسی ارتقاء سطح: {str(e)}")

def check_badges(user, request):
    try:
        user_age_group = user.age_group
        
        stations = Station.objects.filter(is_active=True)
        if user_age_group:
            stations = stations.filter(allowed_age_groups__contains=user_age_group)
        
        completed_stations = UserProgress.objects.filter(user=user).exclude(
            Q(completed_story=False) & Q(completed_prayer=False) & 
            Q(completed_article=False) & Q(completed_video=False) & Q(completed_quiz=False)
        ).count()
        
        total_stations = stations.count()
        
        badge_definitions = [
            ('عارف مهدوی', 'برای تکمیل بیش از 80% ایستگاه‌ها', 800, int(total_stations * 0.8), 
             lambda: completed_stations >= total_stations * 0.8),
            ('دعاخوان نیمه شعبان', 'برای تکمیل ۵ محتوای دعا', 500, 0,
             lambda: UserProgress.objects.filter(user=user, completed_prayer=True).count() >= 5),
            ('هنرمند حضرت', 'برای تکمیل ۳ محتوای داستان', 300, 0,
             lambda: UserProgress.objects.filter(user=user, completed_story=True).count() >= 3),
            ('خدمتگزار منتظر', 'برای کسب ۱۰۰۰ امتیاز', 1000, 0,
             lambda: user.points >= 1000),
        ]
        
        for name, desc, points_required, stations_required, condition in badge_definitions:
            if condition():
                badge, created = Badge.objects.get_or_create(
                    name=name,
                    defaults={
                        'description': desc,
                        'points_required': points_required,
                        'stations_required': stations_required,
                        'allowed_age_groups': user_age_group
                    }
                )
                user_badge, created = UserBadge.objects.get_or_create(user=user, badge=badge)
                if created:
                    messages.success(request, f'تبریک! نشان {badge.name} را دریافت کردید!')
    except Exception as e:
        print(f"خطا در بررسی نشان‌ها: {str(e)}")

def quran(request):
    try:
        user_age_group = request.user.age_group if request.user.is_authenticated else None
        age_group_settings = AgeGroupSettings.objects.filter(
            age_group=user_age_group, is_active=True
        ).first() if user_age_group else None
        
        return render(request, 'quran.html', {
            'user_age_group': user_age_group,
            'age_group_settings': age_group_settings,
        })
    except Exception as e:
        messages.error(request, f'خطا در بارگذاری صفحه قرآن: {str(e)}')
        return render(request, 'quran.html', {})

@login_required
def api_user_progress(request):
    try:
        user = request.user
        user_age_group = user.age_group
        
        stations = Station.objects.filter(is_active=True)
        if user_age_group:
            stations = stations.filter(allowed_age_groups__contains=user_age_group)
        
        return JsonResponse({
            'points': user.points,
            'level': user.spiritual_level,
            'age_group': user_age_group,
            'completed_stations': UserProgress.objects.filter(user=user).exclude(
                Q(completed_story=False) & Q(completed_prayer=False) & 
                Q(completed_article=False) & Q(completed_video=False) & Q(completed_quiz=False)
            ).count(),
            'total_stations': stations.count(),
        })
    except Exception as e:
        return JsonResponse({'error': f'خطا در دریافت اطلاعات: {str(e)}'}, status=500)

@login_required
def admin_dashboard(request):
    try:
        if not request.user.is_superuser:
            messages.error(request, 'شما دسترسی به این بخش را ندارید')
            return redirect('index')
        
        total_users = CustomUser.objects.count()
        total_stations = Station.objects.count()
        age_group_stats = CustomUser.objects.values('age_group').annotate(count=Count('id'))
        
        return render(request, 'admin_dashboard.html', {
            'total_users': total_users,
            'total_stations': total_stations,
            'age_group_stats': age_group_stats,
        })
    except Exception as e:
        messages.error(request, f'خطا در بارگذاری داشبورد مدیریت: {str(e)}')
        return redirect('index')

@login_required
def user_achievements(request):
    try:
        user = request.user
        user_age_group = user.age_group
        badges = UserBadge.objects.filter(user=user).select_related('badge')
        
        age_group_settings = AgeGroupSettings.objects.filter(
            age_group=user_age_group, is_active=True
        ).first()
        
        return render(request, 'user_achievements.html', {
            'badges': badges,
            'user_age_group': user_age_group,
            'age_group_settings': age_group_settings,
        })
    except Exception as e:
        messages.error(request, f'خطا در بارگذاری دستاوردها: {str(e)}')
        return redirect('dashboard')

@login_required
def user_statistics(request):
    try:
        user = request.user
        user_age_group = user.age_group
        
        stations = Station.objects.filter(is_active=True)
        if user_age_group:
            stations = stations.filter(allowed_age_groups__contains=user_age_group)
        
        total_stations = stations.count()
        user_progress = UserProgress.objects.filter(user=user)
        
        stats = {
            'total_stations': total_stations,
            'completed_stations': user_progress.exclude(
                Q(completed_story=False) & Q(completed_prayer=False) & 
                Q(completed_article=False) & Q(completed_video=False) & Q(completed_quiz=False)
            ).count(),
            'completed_stories': user_progress.filter(completed_story=True).count(),
            'completed_prayers': user_progress.filter(completed_prayer=True).count(),
            'completed_articles': user_progress.filter(completed_article=True).count(),
            'completed_videos': user_progress.filter(completed_video=True).count(),
            'completed_quizzes': user_progress.filter(completed_quiz=True).count(),
            'total_points': user.points,
            'spiritual_level': user.get_spiritual_level_display(),
        }
        
        age_group_settings = AgeGroupSettings.objects.filter(
            age_group=user_age_group, is_active=True
        ).first()
        
        return render(request, 'user_statistics.html', {
            **stats,
            'user_age_group': user_age_group,
            'age_group_settings': age_group_settings,
        })
    except Exception as e:
        messages.error(request, f'خطا در بارگذاری آمار: {str(e)}')
        return redirect('dashboard')

@login_required
def user_daily_stats(request):
    try:
        today = timezone.now().date()
        today_completions = UserProgress.objects.filter(
            user=request.user, completion_date__date=today
        ).count()
        
        user_age_group = request.user.age_group
        age_group_settings = AgeGroupSettings.objects.filter(
            age_group=user_age_group, is_active=True
        ).first()
        
        return render(request, 'user_daily_stats.html', {
            'today_completions': today_completions,
            'date': today,
            'user_age_group': user_age_group,
            'age_group_settings': age_group_settings,
        })
    except Exception as e:
        messages.error(request, f'خطا در بارگذاری آمار روزانه: {str(e)}')
        return redirect('dashboard')

def station_leaderboard(request):
    try:
        leaderboard = CustomUser.objects.filter(is_active=True).annotate(
            total_completed_stations=Count('userprogress', filter=~Q(
                Q(userprogress__completed_story=False) & 
                Q(userprogress__completed_prayer=False) & 
                Q(userprogress__completed_article=False) & 
                Q(userprogress__completed_video=False) & 
                Q(userprogress__completed_quiz=False)
            ))
        ).order_by('-points', '-total_completed_stations')[:20]
        
        user_age_group = request.user.age_group if request.user.is_authenticated else None
        age_group_settings = AgeGroupSettings.objects.filter(
            age_group=user_age_group, is_active=True
        ).first() if user_age_group else None
        
        return render(request, 'leaderboard.html', {
            'leaderboard': leaderboard,
            'user_age_group': user_age_group,
            'age_group_settings': age_group_settings,
        })
    except Exception as e:
        messages.error(request, f'خطا در بارگذاری جدول رتبه‌بندی: {str(e)}')
        return render(request, 'leaderboard.html', {})

def handler404(request, exception):
    return render(request, '404.html', status=404)

def handler500(request):
    return render(request, '500.html', status=500)

def handler403(request, exception):
    return render(request, '403.html', status=403)

def handler400(request, exception):
    return render(request, '400.html', status=400)

def time(request):
    try:
        user_age_group = request.user.age_group if request.user.is_authenticated else None
        age_group_settings = AgeGroupSettings.objects.filter(
            age_group=user_age_group, is_active=True
        ).first() if user_age_group else None
        
        return render(request, 'time.html', {
            'user_age_group': user_age_group,
            'age_group_settings': age_group_settings,
        })
    except Exception as e:
        messages.error(request, f'خطا در بارگذاری صفحه اوقات شرعی: {str(e)}')
        return render(request, 'time.html', {})

def games_list(request):
    try:
        user_age_group = request.user.age_group if request.user.is_authenticated else None
        
        games = Game.objects.filter(is_active=True, status='published')
        if user_age_group:
            games = games.filter(allowed_age_groups__contains=user_age_group)
        games = games.order_by('order', '-created_date')
        
        user_progress_dict = {}
        if request.user.is_authenticated:
            user_progress_list = UserGameProgress.objects.filter(
                user=request.user, game__in=games
            ).select_related('game')
            user_progress_dict = {progress.game_id: progress for progress in user_progress_list}
        
        age_group_settings = AgeGroupSettings.objects.filter(
            age_group=user_age_group, is_active=True
        ).first() if user_age_group else None
        
        return render(request, 'games_list.html', {
            'games': games,
            'user_progress': user_progress_dict,
            'user_age_group': user_age_group,
            'age_group_settings': age_group_settings,
        })
    except Exception as e:
        messages.error(request, f'خطا در بارگذاری لیست بازی‌ها: {str(e)}')
        return render(request, 'games_list.html', {})

@login_required
def play_game(request, game_id):
    try:
        game = get_object_or_404(Game, id=game_id, is_active=True, status='published')
        user_age_group = request.user.age_group
        
        if not game.is_allowed_for_age_group(user_age_group):
            messages.error(request, 'شما دسترسی به این بازی را ندارید')
            return redirect('games_list')
        
        user_progress, created = UserGameProgress.objects.get_or_create(
            user=request.user, game=game
        )
        
        user_progress.play_count += 1
        user_progress.last_played = timezone.now()
        user_progress.save()
        
        html_content = ""
        if game.html_file:
            try:
                with open(game.html_file.path, 'r', encoding='utf-8') as f:
                    html_content = f.read()
            except:
                html_content = "<p>خطا در بارگذاری بازی</p>"
        
        age_group_settings = AgeGroupSettings.objects.filter(
            age_group=user_age_group, is_active=True
        ).first()
        
        return render(request, 'play_game.html', {
            'game': game,
            'user_progress': user_progress,
            'html_content': html_content,
            'user_age_group': user_age_group,
            'age_group_settings': age_group_settings,
        })
    except Exception as e:
        messages.error(request, f'خطا در بارگذاری بازی: {str(e)}')
        return redirect('games_list')

@login_required
def complete_game(request, game_id):
    try:
        if request.method != 'POST':
            return JsonResponse({'success': False, 'error': 'درخواست نامعتبر'})
        
        game = get_object_or_404(Game, id=game_id, is_active=True, status='published')
        user_age_group = request.user.age_group
        
        if not game.is_allowed_for_age_group(user_age_group):
            return JsonResponse({'success': False, 'error': 'دسترسی غیرمجاز'})
        
        user_progress, created = UserGameProgress.objects.get_or_create(
            user=request.user, game=game
        )
        
        score = request.POST.get('score', 0)
        try:
            score = int(score)
        except (ValueError, TypeError):
            score = 0
        
        if not user_progress.completed:
            user_progress.score = score
            user_progress.completed = True
            user_progress.completion_date = timezone.now()
            user_progress.save()
            
            request.user.points += game.points_reward
            request.user.save()
            
            check_level_up(request.user, request)
            check_badges(request.user, request)
            
            return JsonResponse({
                'success': True,
                'points_added': game.points_reward,
                'message': f'تبریک! {game.points_reward} امتیاز دریافت کردید!'
            })
        else:
            return JsonResponse({
                'success': True,
                'points_added': 0,
                'message': 'شما قبلاً این بازی را تکمیل کرده‌اید'
            })
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})

@login_required
def game_management(request):
    try:
        if not request.user.is_superuser:
            messages.error(request, 'شما دسترسی به این بخش را ندارید')
            return redirect('games_list')
        
        if request.method == 'POST':
            form = GameForm(request.POST, request.FILES)
            if form.is_valid():
                form.save()
                messages.success(request, 'بازی با موفقیت اضافه شد')
                return redirect('game_management')
        else:
            form = GameForm()
        
        games = Game.objects.all().order_by('order', '-created_date')
        
        return render(request, 'game_management.html', {
            'form': form,
            'games': games,
        })
    except Exception as e:
        messages.error(request, f'خطا در مدیریت بازی‌ها: {str(e)}')
        return redirect('games_list')

@login_required
def delete_game(request, game_id):
    try:
        if not request.user.is_superuser:
            messages.error(request, 'شما دسترسی به این بخش را ندارید')
            return redirect('game_management')
        
        game = get_object_or_404(Game, id=game_id)
        game.delete()
        messages.success(request, 'بازی با موفقیت حذف شد')
        return redirect('game_management')
    except Exception as e:
        messages.error(request, f'خطا در حذف بازی: {str(e)}')
        return redirect('game_management')

@login_required
def chat_home(request):
    try:
        rooms = ChatRoom.objects.filter(
            participants=request.user, is_active=True
        ).order_by('-last_activity')
        
        rooms_with_unread = []
        for room in rooms:
            unread_count = ChatMessage.objects.filter(
                room=room, is_read=False
            ).exclude(sender=request.user).count()
            rooms_with_unread.append({'room': room, 'unread_count': unread_count})
        
        user_age_group = request.user.age_group
        age_group_settings = AgeGroupSettings.objects.filter(
            age_group=user_age_group, is_active=True
        ).first()
        
        return render(request, 'chat/chat_home.html', {
            'rooms_with_unread': rooms_with_unread,
            'user_age_group': user_age_group,
            'age_group_settings': age_group_settings,
        })
    except Exception as e:
        messages.error(request, f'خطا در بارگذاری صفحه چت: {str(e)}')
        return render(request, 'chat/chat_home.html', {})

@login_required
def chat_room(request, room_id):
    try:
        room = get_object_or_404(
            ChatRoom, id=room_id, participants=request.user, is_active=True
        )
        
        chat_messages = ChatMessage.objects.filter(
            room=room
        ).select_related('sender').order_by('created_date')
        
        unread_messages = chat_messages.filter(is_read=False).exclude(sender=request.user)
        for message in unread_messages:
            message.is_read = True
            message.save()
            MessageReadReceipt.objects.get_or_create(message=message, user=request.user)
        
        if request.method == 'POST':
            content = request.POST.get('content', '').strip()
            image = request.FILES.get('image')
            file = request.FILES.get('file')
            audio = request.FILES.get('audio')
            video = request.FILES.get('video')
            sticker = request.POST.get('sticker', '')
            
            if not (content or image or file or audio or video or sticker):
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return JsonResponse({'success': False, 'error': 'لطفاً پیام یا فایلی را انتخاب کنید'})
                return redirect('chat_room', room_id=room_id)
            
            message = ChatMessage(room=room, sender=request.user, content=content)
            
            if image:
                message.image = image
                message.message_type = 'image'
                message.content = message.content or '📷 عکس'
            elif file:
                message.file = file
                message.message_type = 'file'
                message.file_name = file.name
                message.file_size = file.size
                message.content = message.content or '📎 فایل'
            elif audio:
                message.audio = audio
                message.message_type = 'audio'
                message.file_name = audio.name
                message.file_size = audio.size
                message.content = message.content or '🎵 صوت'
            elif video:
                message.video = video
                message.message_type = 'video'
                message.file_name = video.name
                message.file_size = video.size
                message.content = message.content or '🎬 ویدیو'
            elif sticker:
                message.sticker = sticker
                message.message_type = 'sticker'
                message.content = sticker
            else:
                message.message_type = 'text'
            
            message.save()
            
            room.last_activity = timezone.now()
            room.save()
            
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': True,
                    'message_id': message.id,
                    'message_type': message.message_type,
                    'content': message.content,
                    'image_url': message.image.url if message.image else None,
                    'file_url': message.file.url if message.file else None,
                    'audio_url': message.audio.url if message.audio else None,
                    'video_url': message.video.url if message.video else None,
                    'sticker': message.sticker,
                    'file_name': message.file_name,
                    'file_size': message.get_file_size_display(),
                    'created_date': message.created_date.strftime('%H:%M'),
                    'sender_name': message.sender.get_full_name(),
                })
        
        user_age_group = request.user.age_group
        age_group_settings = AgeGroupSettings.objects.filter(
            age_group=user_age_group, is_active=True
        ).first()
        
        return render(request, 'chat/chat_room.html', {
            'room': room,
            'chat_messages': chat_messages,
            'user_age_group': user_age_group,
            'age_group_settings': age_group_settings,
        })
    except Exception as e:
        messages.error(request, f'خطا در بارگذاری اتاق چت: {str(e)}')
        return redirect('chat_home')

@login_required
def api_chat_messages(request, room_id):
    try:
        room = get_object_or_404(
            ChatRoom, id=room_id, participants=request.user, is_active=True
        )
        
        last_message_id = request.GET.get('last_message_id', 0)
        try:
            last_message_id = int(last_message_id)
        except (ValueError, TypeError):
            last_message_id = 0
        
        new_messages = ChatMessage.objects.filter(
            room=room, id__gt=last_message_id
        ).select_related('sender').order_by('created_date')
        
        messages_data = []
        for message in new_messages:
            messages_data.append({
                'id': message.id,
                'sender_id': message.sender.id,
                'sender_name': message.sender.get_full_name(),
                'message_type': message.message_type,
                'content': message.content,
                'image_url': message.image.url if message.image else None,
                'file_url': message.file.url if message.file else None,
                'audio_url': message.audio.url if message.audio else None,
                'video_url': message.video.url if message.video else None,
                'sticker': message.sticker,
                'file_name': message.file_name,
                'file_size': message.get_file_size_display(),
                'created_date': message.created_date.strftime('%H:%M'),
                'is_own': message.sender == request.user,
            })
        
        return JsonResponse({
            'success': True,
            'messages': messages_data,
            'has_new_messages': new_messages.exists()
        })
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})

@login_required
def create_chat_room(request):
    try:
        if request.method == 'POST':
            form = ChatRoomForm(request.POST)
            if form.is_valid():
                room = form.save(commit=False)
                room.created_by = request.user
                room.save()
                room.participants.add(request.user)
                room.admins.add(request.user)
                return redirect('chat_room', room_id=room.id)
        else:
            form = ChatRoomForm()
        
        user_age_group = request.user.age_group
        age_group_settings = AgeGroupSettings.objects.filter(
            age_group=user_age_group, is_active=True
        ).first()
        
        return render(request, 'chat/create_room.html', {
            'form': form,
            'user_age_group': user_age_group,
            'age_group_settings': age_group_settings,
        })
    except Exception as e:
        messages.error(request, f'خطا در ایجاد اتاق چت: {str(e)}')
        return redirect('chat_home')

@login_required
def create_private_chat(request, user_id):
    try:
        other_user = get_object_or_404(CustomUser, id=user_id, is_active=True)
        
        if other_user == request.user:
            return redirect('chat_home')
        
        existing_room = ChatRoom.objects.filter(
            room_type='private', participants=request.user
        ).filter(participants=other_user).first()
        
        if existing_room:
            return redirect('chat_room', room_id=existing_room.id)
        
        room = ChatRoom.objects.create(
            name=f"{request.user.get_full_name()} و {other_user.get_full_name()}",
            room_type='private',
            created_by=request.user
        )
        room.participants.add(request.user, other_user)
        
        return redirect('chat_room', room_id=room.id)
    except Exception as e:
        messages.error(request, f'خطا در ایجاد چت خصوصی: {str(e)}')
        return redirect('chat_home')

@login_required
def manage_chat_room(request, room_id):
    try:
        room = get_object_or_404(
            ChatRoom, id=room_id, participants=request.user, is_active=True
        )
        
        if not (room.created_by == request.user or request.user in room.admins.all()):
            messages.error(request, 'شما دسترسی مدیریت این اتاق را ندارید')
            return redirect('chat_room', room_id=room_id)
        
        if request.method == 'POST':
            action = request.POST.get('action')
            
            if action == 'add_participants':
                form = AddParticipantForm(request.POST)
                if form.is_valid():
                    phone = form.cleaned_data['phone']
                    user_to_add = CustomUser.objects.filter(phone=phone, is_active=True).first()
                    
                    if user_to_add:
                        if user_to_add not in room.participants.all():
                            room.participants.add(user_to_add)
                            messages.success(request, f'کاربر {user_to_add.get_full_name()} به گروه اضافه شد')
                        else:
                            messages.info(request, 'این کاربر قبلاً در گروه عضو است')
                    else:
                        messages.error(request, 'کاربری با این شماره تلفن یافت نشد')
                    
                    return redirect('manage_chat_room', room_id=room_id)
            
            elif action == 'remove_participant':
                user_id = request.POST.get('user_id')
                user_to_remove = get_object_or_404(CustomUser, id=user_id)
                
                if user_to_remove != request.user and user_to_remove != room.created_by:
                    room.participants.remove(user_to_remove)
                    room.admins.remove(user_to_remove)
                    messages.success(request, f'کاربر {user_to_remove.get_full_name()} از اتاق حذف شد')
                else:
                    messages.error(request, 'نمی‌توانید خودتان یا سازنده اتاق را حذف کنید')
                
                return redirect('manage_chat_room', room_id=room_id)
            
            elif action == 'toggle_admin':
                user_id = request.POST.get('user_id')
                user_to_toggle = get_object_or_404(CustomUser, id=user_id)
                
                if user_to_toggle in room.participants.all() and user_to_toggle != room.created_by:
                    if room.admins.filter(id=user_to_toggle.id).exists():
                        room.admins.remove(user_to_toggle)
                        messages.success(request, f'دسترسی مدیریت {user_to_toggle.get_full_name()} حذف شد')
                    else:
                        room.admins.add(user_to_toggle)
                        messages.success(request, f'دسترسی مدیریت به {user_to_toggle.get_full_name()} داده شد')
                else:
                    messages.error(request, 'عملیات نامعتبر')
                
                return redirect('manage_chat_room', room_id=room_id)
            
            elif action == 'delete_room':
                if room.created_by == request.user:
                    room.is_active = False
                    room.save()
                    messages.success(request, 'اتاق چت حذف شد')
                    return redirect('chat_home')
                else:
                    messages.error(request, 'فقط سازنده اتاق می‌تواند آن را حذف کند')
        
        add_participant_form = AddParticipantForm()
        user_age_group = request.user.age_group
        age_group_settings = AgeGroupSettings.objects.filter(
            age_group=user_age_group, is_active=True
        ).first()
        
        return render(request, 'chat/manage_room.html', {
            'room': room,
            'add_participant_form': add_participant_form,
            'user_age_group': user_age_group,
            'age_group_settings': age_group_settings,
        })
    except Exception as e:
        messages.error(request, f'خطا در مدیریت اتاق چت: {str(e)}')
        return redirect('chat_home')

@login_required
def leave_chat_room(request, room_id):
    try:
        room = get_object_or_404(
            ChatRoom, id=room_id, participants=request.user, is_active=True
        )
        
        if room.created_by == request.user:
            messages.error(request, 'شما سازنده اتاق هستید و نمی‌توانید آن را ترک کنید. ابتدا اتاق را حذف کنید.')
            return redirect('chat_room', room_id=room_id)
        
        room.participants.remove(request.user)
        room.admins.remove(request.user)
        
        messages.success(request, 'اتاق چت را ترک کردید')
        return redirect('chat_home')
    except Exception as e:
        messages.error(request, f'خطا در ترک اتاق چت: {str(e)}')
        return redirect('chat_home')

@login_required
def search_users(request):
    try:
        query = request.GET.get('q', '')
        users = CustomUser.objects.filter(is_active=True)
        
        if query:
            users = users.filter(phone=query).exclude(id=request.user.id)
        
        user_age_group = request.user.age_group
        age_group_settings = AgeGroupSettings.objects.filter(
            age_group=user_age_group, is_active=True
        ).first()
        
        return render(request, 'chat/search_users.html', {
            'users': users,
            'query': query,
            'user_age_group': user_age_group,
            'age_group_settings': age_group_settings,
        })
    except Exception as e:
        messages.error(request, f'خطا در جستجوی کاربران: {str(e)}')
        return render(request, 'chat/search_users.html', {})

@login_required
def api_send_message(request, room_id):
    try:
        if request.method != 'POST':
            return JsonResponse({'success': False, 'error': 'درخواست نامعتبر'})
        
        room = get_object_or_404(
            ChatRoom, id=room_id, participants=request.user, is_active=True
        )
        
        content = request.POST.get('content', '').strip()
        image = request.FILES.get('image')
        file = request.FILES.get('file')
        audio = request.FILES.get('audio')
        video = request.FILES.get('video')
        sticker = request.POST.get('sticker', '')
        
        if not (content or image or file or audio or video or sticker):
            return JsonResponse({'success': False, 'error': 'پیام نمی‌تواند خالی باشد'})
        
        message = ChatMessage(room=room, sender=request.user, content=content)
        
        if image:
            message.image = image
            message.message_type = 'image'
        elif file:
            message.file = file
            message.file_name = file.name
            message.file_size = file.size
            message.message_type = 'file'
        elif audio:
            message.audio = audio
            message.file_name = audio.name
            message.file_size = audio.size
            message.message_type = 'audio'
        elif video:
            message.video = video
            message.file_name = video.name
            message.file_size = video.size
            message.message_type = 'video'
        elif sticker:
            message.sticker = sticker
            message.message_type = 'sticker'
        
        message.save()
        
        room.last_activity = timezone.now()
        room.save()
        
        return JsonResponse({
            'success': True,
            'message_id': message.id,
            'created_date': message.created_date.isoformat(),
        })
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})

def zecr(request):
    try:
        user_age_group = request.user.age_group if request.user.is_authenticated else None
        age_group_settings = AgeGroupSettings.objects.filter(
            age_group=user_age_group, is_active=True
        ).first() if user_age_group else None
        
        return render(request, 'zecr.html', {
            'user_age_group': user_age_group,
            'age_group_settings': age_group_settings,
        })
    except Exception as e:
        messages.error(request, f'خطا در بارگذاری صفحه ذکر: {str(e)}')
        return render(request, 'zecr.html', {})

class ActiveAudioView(View):
    def get(self, request):
        try:
            user_age_group = request.user.age_group if request.user.is_authenticated else None
            
            audio_files = AudioFile.objects.filter(is_active=True)
            if user_age_group:
                audio_files = audio_files.filter(allowed_age_groups__contains=user_age_group)
            
            active_audio = audio_files.first()
            
            if active_audio and active_audio.audio_file:
                return JsonResponse({
                    'success': True,
                    'url': active_audio.audio_file.url,
                    'title': active_audio.title,
                    'filename': active_audio.audio_file.name
                })
            return JsonResponse({'success': False, 'error': 'فایل صوتی فعالی یافت نشد'}, status=404)
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)}, status=500)

class BaseView(TemplateView):
    template_name = 'base.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user_age_group = self.request.user.age_group if self.request.user.is_authenticated else None
        
        audio_files = AudioFile.objects.filter(is_active=True)
        if user_age_group:
            audio_files = audio_files.filter(allowed_age_groups__contains=user_age_group)
        
        active_audio = audio_files.first()
        if active_audio:
            context['active_audio'] = active_audio
        
        age_group_settings = AgeGroupSettings.objects.filter(
            age_group=user_age_group, is_active=True
        ).first() if user_age_group else None
        
        context['user_age_group'] = user_age_group
        context['age_group_settings'] = age_group_settings
        
        return context

def shop_home(request):
    try:
        categories = ProductCategory.objects.filter(is_active=True).order_by('order')
        
        user_age_group = request.user.age_group if request.user.is_authenticated else None
        
        base_products = Product.objects.filter(is_active=True, status='published', stock_quantity__gt=0)
        
        if user_age_group:
            base_products = base_products.filter(allowed_age_groups__contains=user_age_group)
        
        featured_products = base_products.filter(is_featured=True).order_by('order', '-created_at')[:8]
        new_products = base_products.order_by('-created_at')[:8]
        
        popular_products = Product.objects.filter(
            is_active=True, status='published', stock_quantity__gt=0
        ).annotate(order_count=Count('orderitem__id')).order_by('-order_count')[:6]
        
        age_group_settings = AgeGroupSettings.objects.filter(
            age_group=user_age_group, is_active=True
        ).first() if user_age_group else None
        
        return render(request, 'shop/shop_home.html', {
            'categories': categories,
            'featured_products': featured_products,
            'new_products': new_products,
            'popular_products': popular_products,
            'user_age_group': user_age_group,
            'age_group_settings': age_group_settings,
        })
    except Exception as e:
        messages.error(request, f'خطا در بارگذاری صفحه فروشگاه: {str(e)}')
        return render(request, 'shop/shop_home.html', {})

def product_list(request):
    try:
        search_query = request.GET.get('q', '')
        category_id = request.GET.get('category', '')
        sort_by = request.GET.get('sort', 'newest')
        
        user_age_group = request.user.age_group if request.user.is_authenticated else None
        
        products = Product.objects.filter(is_active=True, status='published')
        
        if user_age_group:
            products = products.filter(allowed_age_groups__contains=user_age_group)
        
        if search_query:
            products = products.filter(
                Q(name__icontains=search_query) | 
                Q(description__icontains=search_query) |
                Q(short_description__icontains=search_query) |
                Q(category__name__icontains=search_query)
            )
        
        if category_id:
            try:
                products = products.filter(category_id=int(category_id))
            except (ValueError, TypeError):
                pass
        
        sort_options = {
            'price_low': 'final_price',
            'price_high': '-final_price',
            'name': 'name',
            'popular': '-order_count',
            'newest': '-created_at'
        }
        
        if sort_by == 'popular':
            products = products.annotate(order_count=Count('orderitem__id'))
        
        products = products.order_by(sort_options.get(sort_by, '-created_at'))
        
        paginator = Paginator(products, 12)
        page_obj = paginator.get_page(request.GET.get('page'))
        
        categories = ProductCategory.objects.filter(is_active=True).annotate(
            active_products_count=Count(
                'products', filter=Q(products__is_active=True, products__status='published')
            )
        ).order_by('order')
        
        age_group_settings = AgeGroupSettings.objects.filter(
            age_group=user_age_group, is_active=True
        ).first() if user_age_group else None
        
        return render(request, 'shop/product_list.html', {
            'products': page_obj,
            'categories': categories,
            'search_query': search_query,
            'selected_category': category_id,
            'sort_by': sort_by,
            'user_age_group': user_age_group,
            'age_group_settings': age_group_settings,
        })
    except Exception as e:
        messages.error(request, f'خطا در بارگذاری لیست محصولات: {str(e)}')
        return redirect('shop_home')

def product_detail(request, product_id):
    try:
        product = get_object_or_404(Product, id=product_id, is_active=True)
        
        user_age_group = request.user.age_group if request.user.is_authenticated else None
        
        if user_age_group and not product.is_allowed_for_age_group(user_age_group):
            messages.error(request, 'شما دسترسی به این محصول را ندارید')
            return redirect('product_list')
        
        related_products = Product.objects.filter(
            category=product.category,
            is_active=True,
            status='published'
        ).exclude(id=product.id).order_by('?')[:4]
        
        reviews = product.reviews.filter(is_approved=True).select_related('user').order_by('-created_at')
        
        review_stats = reviews.aggregate(
            avg_rating=Avg('rating'),
            total_reviews=Count('id'),
            rating_5=Count('id', filter=Q(rating=5)),
            rating_4=Count('id', filter=Q(rating=4)),
            rating_3=Count('id', filter=Q(rating=3)),
            rating_2=Count('id', filter=Q(rating=2)),
            rating_1=Count('id', filter=Q(rating=1)),
        )
        
        in_wishlist = False
        user_review = None
        
        if request.user.is_authenticated:
            in_wishlist = Wishlist.objects.filter(user=request.user, product=product).exists()
            user_review = ProductReview.objects.filter(user=request.user, product=product).first()
        
        age_group_settings = AgeGroupSettings.objects.filter(
            age_group=user_age_group, is_active=True
        ).first() if user_age_group else None
        
        return render(request, 'shop/product_detail.html', {
            'product': product,
            'related_products': related_products,
            'reviews': reviews,
            'review_stats': review_stats,
            'avg_rating': round(review_stats.get('avg_rating') or 0, 1),
            'review_count': reviews.count(),
            'in_wishlist': in_wishlist,
            'user_review': user_review,
            'review_form': ProductReviewForm() if request.user.is_authenticated and not user_review else None,
            'user_age_group': user_age_group,
            'age_group_settings': age_group_settings,
        })
    except Exception as e:
        messages.error(request, f'خطا در بارگذاری محصول: {str(e)}')
        return redirect('product_list')

@login_required
def add_to_wishlist(request, product_id):
    try:
        product = get_object_or_404(Product, id=product_id, is_active=True)
        user_age_group = request.user.age_group
        
        if not product.is_allowed_for_age_group(user_age_group):
            messages.error(request, 'شما دسترسی به این محصول را ندارید')
            return redirect('product_detail', product_id=product_id)
        
        wishlist_item, created = Wishlist.objects.get_or_create(
            user=request.user, product=product
        )
        
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'success': True,
                'action': 'added' if created else 'already_exists',
                'message': 'محصول به علاقه‌مندی‌ها اضافه شد' if created else 'این محصول قبلاً در لیست علاقه‌مندی‌های شماست'
            })
        
        messages.success(request, 'محصول به لیست علاقه‌مندی‌ها اضافه شد' if created else 'این محصول قبلاً در لیست علاقه‌مندی‌های شماست')
        return redirect('product_detail', product_id=product_id)
    except Exception as e:
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'success': False, 'error': 'خطا در افزودن به علاقه‌مندی‌ها'})
        messages.error(request, f'خطا در افزودن به علاقه‌مندی‌ها: {str(e)}')
        return redirect('product_detail', product_id=product_id)

@login_required
def remove_from_wishlist(request, product_id):
    try:
        product = get_object_or_404(Product, id=product_id)
        
        deleted = Wishlist.objects.filter(user=request.user, product=product).delete()[0] > 0
        
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'success': True,
                'action': 'removed' if deleted else 'not_found',
                'message': 'محصول از علاقه‌مندی‌ها حذف شد' if deleted else 'این محصول در لیست علاقه‌مندی‌های شما نبود'
            })
        
        messages.success(request, 'محصول از لیست علاقه‌مندی‌ها حذف شد' if deleted else 'این محصول در لیست علاقه‌مندی‌های شما نبود')
        return redirect('product_detail', product_id=product_id)
    except Exception as e:
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'success': False, 'error': 'خطا در حذف از علاقه‌مندی‌ها'})
        messages.error(request, f'خطا در حذف از علاقه‌مندی‌ها: {str(e)}')
        return redirect('product_detail', product_id=product_id)

@login_required
def wishlist_view(request):
    try:
        wishlist_items = Wishlist.objects.filter(user=request.user).select_related('product')
        
        inactive_products = wishlist_items.filter(
            Q(product__is_active=False) | 
            Q(product__status__in=['draft', 'out_of_stock'])
        )
        if inactive_products.exists():
            inactive_products.delete()
            wishlist_items = Wishlist.objects.filter(user=request.user).select_related('product')
        
        user_age_group = request.user.age_group
        age_group_settings = AgeGroupSettings.objects.filter(
            age_group=user_age_group, is_active=True
        ).first()
        
        return render(request, 'shop/wishlist.html', {
            'wishlist_items': wishlist_items,
            'user_age_group': user_age_group,
            'age_group_settings': age_group_settings,
        })
    except Exception as e:
        messages.error(request, f'خطا در بارگذاری لیست علاقه‌مندی‌ها: {str(e)}')
        return redirect('shop_home')

@login_required
def add_to_cart(request, product_id):
    try:
        product = get_object_or_404(
            Product, id=product_id, is_active=True, status='published'
        )
        user_age_group = request.user.age_group
        
        if not product.is_allowed_for_age_group(user_age_group):
            messages.error(request, 'شما دسترسی به این محصول را ندارید')
            return redirect('product_detail', product_id=product_id)
        
        if not product.is_available:
            messages.error(request, 'این محصول در حال حاضر موجود نمی‌باشد')
            return redirect('product_detail', product_id=product_id)
        
        quantity = int(request.POST.get('quantity', 1))
        
        if quantity <= 0 or quantity > product.stock_quantity:
            messages.error(request, f'تعداد نامعتبر. موجودی: {product.stock_quantity}')
            return redirect('product_detail', product_id=product_id)
        
        cart_item, created = Cart.objects.get_or_create(
            user=request.user,
            product=product,
            defaults={'quantity': quantity}
        )
        
        if not created:
            new_quantity = cart_item.quantity + quantity
            if new_quantity > product.stock_quantity:
                messages.error(request, f'تعداد کل بیشتر از موجودی است. موجودی: {product.stock_quantity}')
                return redirect('product_detail', product_id=product_id)
            
            cart_item.quantity = new_quantity
            cart_item.save()
            messages.success(request, f'تعداد محصول در سبد خرید به {new_quantity} عدد افزایش یافت')
        else:
            messages.success(request, 'محصول به سبد خرید اضافه شد')
        
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'success': True,
                'cart_count': Cart.objects.filter(user=request.user).count(),
                'message': 'محصول به سبد خرید اضافه شد'
            })
        
        return redirect('product_detail', product_id=product_id)
    except Exception as e:
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'success': False, 'error': 'خطا در افزودن به سبد خرید'})
        messages.error(request, f'خطا در افزودن به سبد خرید: {str(e)}')
        return redirect('product_detail', product_id=product_id)

@login_required
def cart_view(request):
    try:
        cart_items = Cart.objects.filter(user=request.user).select_related('product')
        
        updated = False
        for item in cart_items:
            if item.quantity > item.product.stock_quantity:
                if item.product.stock_quantity == 0:
                    item.delete()
                    messages.warning(request, f'محصول "{item.product.name}" از سبد خرید حذف شد (ناموجود)')
                else:
                    item.quantity = item.product.stock_quantity
                    item.save()
                    messages.warning(request, f'تعداد محصول "{item.product.name}" به {item.product.stock_quantity} عدد کاهش یافت')
                updated = True
        
        if updated:
            cart_items = Cart.objects.filter(user=request.user).select_related('product')
        
        total_price = sum(item.total_price for item in cart_items)
        total_items = sum(item.quantity for item in cart_items)
        
        user_age_group = request.user.age_group
        age_group_settings = AgeGroupSettings.objects.filter(
            age_group=user_age_group, is_active=True
        ).first()
        
        return render(request, 'shop/cart.html', {
            'cart_items': cart_items,
            'total_price': total_price,
            'total_items': total_items,
            'user_age_group': user_age_group,
            'age_group_settings': age_group_settings,
        })
    except Exception as e:
        messages.error(request, f'خطا در بارگذاری سبد خرید: {str(e)}')
        return render(request, 'shop/cart.html', {})

@login_required
def update_cart(request, cart_item_id):
    try:
        cart_item = get_object_or_404(Cart, id=cart_item_id, user=request.user)
        
        action = request.POST.get('action')
        
        if action == 'update':
            quantity = int(request.POST.get('quantity', 1))
            
            if quantity <= 0:
                cart_item.delete()
                messages.success(request, 'محصول از سبد خرید حذف شد')
            elif quantity > cart_item.product.stock_quantity:
                messages.error(request, f'تعداد درخواستی بیشتر از موجودی است. موجودی: {cart_item.product.stock_quantity}')
            else:
                cart_item.quantity = quantity
                cart_item.save()
                messages.success(request, 'تعداد محصول به‌روزرسانی شد')
        
        elif action == 'remove':
            product_name = cart_item.product.name
            cart_item.delete()
            messages.success(request, f'محصول "{product_name}" از سبد خرید حذف شد')
        
        elif action == 'increase':
            if cart_item.can_increase_quantity():
                cart_item.quantity += 1
                cart_item.save()
                messages.success(request, 'تعداد محصول افزایش یافت')
            else:
                messages.error(request, 'امکان افزایش تعداد وجود ندارد')
        
        elif action == 'decrease':
            if cart_item.quantity > 1:
                cart_item.quantity -= 1
                cart_item.save()
                messages.success(request, 'تعداد محصول کاهش یافت')
            else:
                cart_item.delete()
                messages.success(request, 'محصول از سبد خرید حذف شد')
        
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            cart_items = Cart.objects.filter(user=request.user)
            return JsonResponse({
                'success': True,
                'total_price': sum(item.total_price for item in cart_items),
                'total_items': sum(item.quantity for item in cart_items),
                'item_total': cart_item.total_price if action != 'remove' else 0
            })
        
        return redirect('cart_view')
    except Exception as e:
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'success': False, 'error': 'خطا در به‌روزرسانی سبد خرید'})
        messages.error(request, f'خطا در به‌روزرسانی سبد خرید: {str(e)}')
        return redirect('cart_view')

@login_required
def clear_cart(request):
    try:
        Cart.objects.filter(user=request.user).delete()
        
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'success': True, 'message': 'سبد خرید خالی شد', 'cart_count': 0})
        
        messages.success(request, 'سبد خرید با موفقیت خالی شد')
        return redirect('cart_view')
    except Exception as e:
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'success': False, 'error': 'خطا در خالی کردن سبد خرید'})
        messages.error(request, f'خطا در خالی کردن سبد خرید: {str(e)}')
        return redirect('cart_view')

@login_required
def checkout(request):
    try:
        cart_items = Cart.objects.filter(user=request.user).select_related('product')
        
        if not cart_items.exists():
            messages.error(request, 'سبد خرید شما خالی است')
            return redirect('cart_view')
        
        for item in cart_items:
            if item.quantity > item.product.stock_quantity:
                messages.error(request, f'موجودی محصول "{item.product.name}" کافی نیست')
                return redirect('cart_view')
        
        total_price = sum(item.total_price for item in cart_items)
        
        if request.method == 'POST':
            form = CheckoutForm(request.POST)
            if form.is_valid():
                with transaction.atomic():
                    order = Order(
                        user=request.user,
                        total_amount=total_price,
                        customer_name=form.cleaned_data['customer_name'],
                        customer_phone=form.cleaned_data['customer_phone'],
                        customer_address=form.cleaned_data['customer_address'],
                        customer_postal_code=form.cleaned_data['customer_postal_code'],
                        payment_method=form.cleaned_data['payment_method'],
                    )
                    order.save()
                    
                    for cart_item in cart_items:
                        OrderItem.objects.create(
                            order=order,
                            product=cart_item.product,
                            product_name=cart_item.product.name,
                            product_price=cart_item.product.final_price,
                            quantity=cart_item.quantity,
                        )
                        
                        cart_item.product.stock_quantity -= cart_item.quantity
                        cart_item.product.save()
                    
                    cart_items.delete()
                
                messages.success(request, f'سفارش شما با شماره {order.order_number} ثبت شد')
                return redirect('payment_page', order_id=order.id)
        else:
            form = CheckoutForm(initial={
                'customer_name': request.user.get_full_name(),
                'customer_phone': request.user.phone,
            })
        
        user_age_group = request.user.age_group
        age_group_settings = AgeGroupSettings.objects.filter(
            age_group=user_age_group, is_active=True
        ).first()
        
        return render(request, 'shop/checkout.html', {
            'cart_items': cart_items,
            'total_price': total_price,
            'form': form,
            'user_age_group': user_age_group,
            'age_group_settings': age_group_settings,
        })
    except Exception as e:
        messages.error(request, f'خطا در ثبت سفارش: {str(e)}')
        return redirect('cart_view')

@login_required
def payment_page(request, order_id):
    try:
        order = get_object_or_404(Order, id=order_id, user=request.user)
        
        if order.status != 'pending':
            messages.info(request, 'این سفارش قبلاً پرداخت شده است')
            return redirect('order_detail', order_id=order_id)
        
        if request.method == 'POST':
            form = PaymentReceiptForm(request.POST, request.FILES, instance=order)
            if form.is_valid():
                order = form.save(commit=False)
                order.payment_date = timezone.now()
                order.status = 'paid'
                order.save()
                messages.success(request, 'رسید پرداخت با موفقیت آپلود شد. سفارش شما در حال پردازش است.')
                return redirect('order_detail', order_id=order.id)
        else:
            form = PaymentReceiptForm(instance=order)
        
        user_age_group = request.user.age_group
        age_group_settings = AgeGroupSettings.objects.filter(
            age_group=user_age_group, is_active=True
        ).first()
        
        return render(request, 'shop/payment.html', {
            'order': order,
            'form': form,
            'your_card_number': "6037-1234-5678-9012",
            'card_holder_name': "فروشگاه نور مهدی",
            'user_age_group': user_age_group,
            'age_group_settings': age_group_settings,
        })
    except Exception as e:
        messages.error(request, f'خطا در پردازش پرداخت: {str(e)}')
        return redirect('order_list')

@login_required
def order_list(request):
    try:
        orders = Order.objects.filter(user=request.user).prefetch_related('items').order_by('-created_at')
        
        user_age_group = request.user.age_group
        age_group_settings = AgeGroupSettings.objects.filter(
            age_group=user_age_group, is_active=True
        ).first()
        
        return render(request, 'shop/order_list.html', {
            'orders': orders,
            'user_age_group': user_age_group,
            'age_group_settings': age_group_settings,
        })
    except Exception as e:
        messages.error(request, f'خطا در بارگذاری لیست سفارش‌ها: {str(e)}')
        return render(request, 'shop/order_list.html', {})

@login_required
def order_detail(request, order_id):
    try:
        order = get_object_or_404(Order, id=order_id, user=request.user)
        
        user_age_group = request.user.age_group
        age_group_settings = AgeGroupSettings.objects.filter(
            age_group=user_age_group, is_active=True
        ).first()
        
        return render(request, 'shop/order_detail.html', {
            'order': order,
            'user_age_group': user_age_group,
            'age_group_settings': age_group_settings,
        })
    except Exception as e:
        messages.error(request, f'خطا در بارگذاری جزئیات سفارش: {str(e)}')
        return redirect('order_list')

@login_required
def submit_review(request, product_id):
    try:
        product = get_object_or_404(Product, id=product_id, is_active=True)
        user_age_group = request.user.age_group
        
        if not product.is_allowed_for_age_group(user_age_group):
            messages.error(request, 'شما دسترسی به این محصول را ندارید')
            return redirect('product_detail', product_id=product_id)
        
        if ProductReview.objects.filter(user=request.user, product=product).exists():
            messages.error(request, 'شما قبلاً برای این محصول نظر داده‌اید')
            return redirect('product_detail', product_id=product_id)
        
        form = ProductReviewForm(request.POST)
        if form.is_valid():
            review = form.save(commit=False)
            review.product = product
            review.user = request.user
            review.is_approved = request.user.is_superuser or request.user.is_staff
            review.save()
            
            messages.success(request, 'نظر شما با موفقیت ثبت شد' + 
                           (' و پس از تایید نمایش داده می‌شود' if not review.is_approved else ''))
        else:
            messages.error(request, 'خطا در ثبت نظر. لطفاً مجدداً تلاش کنید')
        
        return redirect('product_detail', product_id=product_id)
    except Exception as e:
        messages.error(request, f'خطا در ثبت نظر: {str(e)}')
        return redirect('product_detail', product_id=product_id)

@login_required
def api_cart_count(request):
    try:
        return JsonResponse({'cart_count': Cart.objects.filter(user=request.user).count()})
    except Exception as e:
        return JsonResponse({'cart_count': 0})

def api_product_search(request):
    try:
        query = request.GET.get('q', '')
        limit = int(request.GET.get('limit', 5))
        
        if not query or len(query) < 2:
            return JsonResponse({'products': []})
        
        products = Product.objects.filter(
            Q(name__icontains=query) | Q(description__icontains=query) |
            Q(short_description__icontains=query),
            is_active=True, status='published'
        )[:limit]
        
        return JsonResponse({'products': [{
            'id': p.id,
            'name': p.name,
            'price': str(p.final_price),
            'image_url': p.main_image.url if p.main_image else '',
            'url': p.get_absolute_url()
        } for p in products]})
    except Exception as e:
        return JsonResponse({'products': []})

@login_required
def shop_management(request):
    try:
        if not request.user.is_superuser:
            messages.error(request, 'شما دسترسی به این بخش را ندارید')
            return redirect('shop_home')
        
        total_products = Product.objects.count()
        total_orders = Order.objects.count()
        total_categories = ProductCategory.objects.count()
        pending_orders = Order.objects.filter(status='pending').count()
        total_revenue = Order.objects.filter(status__in=['paid', 'processing', 'shipped', 'delivered']).aggregate(
            total=Sum('total_amount')
        )['total'] or 0
        
        recent_orders = Order.objects.all().select_related('user').order_by('-created_at')[:5]
        low_stock_products = Product.objects.filter(
            stock_quantity__lte=5, stock_quantity__gt=0, is_active=True
        ).order_by('stock_quantity')[:5]
        out_of_stock_products = Product.objects.filter(stock_quantity=0, is_active=True).count()
        
        return render(request, 'shop/admin/shop_management.html', {
            'total_products': total_products,
            'total_orders': total_orders,
            'total_categories': total_categories,
            'pending_orders': pending_orders,
            'total_revenue': total_revenue,
            'recent_orders': recent_orders,
            'low_stock_products': low_stock_products,
            'out_of_stock_products': out_of_stock_products,
        })
    except Exception as e:
        messages.error(request, f'خطا در بارگذاری مدیریت فروشگاه: {str(e)}')
        return redirect('shop_home')

@login_required
def product_management(request):
    try:
        if not request.user.is_superuser:
            messages.error(request, 'شما دسترسی به این بخش را ندارید')
            return redirect('shop_home')
        
        if request.method == 'POST':
            form = ProductForm(request.POST, request.FILES)
            if form.is_valid():
                product = form.save()
                messages.success(request, f'محصول "{product.name}" با موفقیت اضافه شد')
                return redirect('product_management')
        else:
            form = ProductForm()
        
        products = Product.objects.all().select_related('category').order_by('-created_at')
        
        status_filter = request.GET.get('status', 'all')
        if status_filter != 'all':
            products = products.filter(status=status_filter)
        
        category_filter = request.GET.get('category', '')
        if category_filter:
            products = products.filter(category_id=category_filter)
        
        return render(request, 'shop/admin/product_management.html', {
            'form': form,
            'products': products,
            'categories': ProductCategory.objects.filter(is_active=True),
            'status_filter': status_filter,
            'category_filter': category_filter,
        })
    except Exception as e:
        messages.error(request, f'خطا در مدیریت محصولات: {str(e)}')
        return redirect('shop_management')

@login_required
def category_management(request):
    try:
        if not request.user.is_superuser:
            messages.error(request, 'شما دسترسی به این بخش را ندارید')
            return redirect('shop_home')
        
        if request.method == 'POST':
            form = ProductCategoryForm(request.POST, request.FILES)
            if form.is_valid():
                category = form.save()
                messages.success(request, f'دسته‌بندی "{category.name}" با موفقیت اضافه شد')
                return redirect('category_management')
        else:
            form = ProductCategoryForm()
        
        categories = ProductCategory.objects.all().order_by('order')
        
        return render(request, 'shop/admin/category_management.html', {
            'form': form,
            'categories': categories,
        })
    except Exception as e:
        messages.error(request, f'خطا در مدیریت دسته‌بندی‌ها: {str(e)}')
        return redirect('shop_management')

@login_required
def delete_product(request, product_id):
    try:
        if not request.user.is_superuser:
            messages.error(request, 'شما دسترسی به این بخش را ندارید')
            return redirect('product_management')
        
        product = get_object_or_404(Product, id=product_id)
        product_name = product.name
        product.delete()
        
        messages.success(request, f'محصول "{product_name}" با موفقیت حذف شد')
        return redirect('product_management')
    except Exception as e:
        messages.error(request, f'خطا در حذف محصول: {str(e)}')
        return redirect('product_management')

@login_required
def delete_category(request, category_id):
    try:
        if not request.user.is_superuser:
            messages.error(request, 'شما دسترسی به این بخش را ندارید')
            return redirect('category_management')
        
        category = get_object_or_404(ProductCategory, id=category_id)
        
        if category.products.exists():
            messages.error(request, 'امکان حذف دسته‌بندی دارای محصول وجود ندارد')
            return redirect('category_management')
        
        category_name = category.name
        category.delete()
        
        messages.success(request, f'دسته‌بندی "{category_name}" با موفقیت حذف شد')
        return redirect('category_management')
    except Exception as e:
        messages.error(request, f'خطا در حذف دسته‌بندی: {str(e)}')
        return redirect('category_management')

@login_required
def social_home(request):
    try:
        following_users = Follow.objects.filter(follower=request.user).values_list('following', flat=True)
        
        posts = Post.objects.filter(
            user_id__in=following_users, is_active=True
        ).select_related('user').prefetch_related('likes').order_by('-created_at')
        
        twenty_four_hours_ago = timezone.now() - timezone.timedelta(hours=24)
        stories = Story.objects.filter(
            user_id__in=following_users, is_active=True, created_at__gte=twenty_four_hours_ago
        ).select_related('user').order_by('-created_at')
        
        suggested_users = CustomUser.objects.exclude(
            id__in=following_users
        ).exclude(id=request.user.id).order_by('?')[:5]
        
        user_age_group = request.user.age_group
        age_group_settings = AgeGroupSettings.objects.filter(
            age_group=user_age_group, is_active=True
        ).first()
        
        return render(request, 'social/social_home.html', {
            'posts': posts,
            'stories': stories,
            'suggested_users': suggested_users,
            'user_age_group': user_age_group,
            'age_group_settings': age_group_settings,
        })
    except Exception as e:
        messages.error(request, f'خطا در بارگذاری صفحه اجتماعی: {str(e)}')
        return render(request, 'social/social_home.html', {})

@login_required
def social_profile(request, user_id=None):
    try:
        profile_user = get_object_or_404(CustomUser, id=user_id) if user_id else request.user
        
        social_profile, created = SocialProfile.objects.get_or_create(user=profile_user)
        
        posts = Post.objects.filter(user=profile_user, is_active=True).order_by('-created_at')
        stories = Story.objects.filter(user=profile_user, is_active=True, expires_at__gt=timezone.now())
        
        is_following = False
        follow_request_sent = False
        
        if request.user != profile_user:
            is_following = Follow.objects.filter(follower=request.user, following=profile_user).exists()
            if social_profile.is_private:
                follow_request_sent = FollowRequest.objects.filter(
                    from_user=request.user, to_user=profile_user, is_accepted=False
                ).exists()
        
        user_age_group = request.user.age_group
        age_group_settings = AgeGroupSettings.objects.filter(
            age_group=user_age_group, is_active=True
        ).first()
        
        return render(request, 'social/profile.html', {
            'profile_user': profile_user,
            'social_profile': social_profile,
            'posts': posts,
            'stories': stories,
            'is_following': is_following,
            'follow_request_sent': follow_request_sent,
            'is_own_profile': request.user == profile_user,
            'user_age_group': user_age_group,
            'age_group_settings': age_group_settings,
        })
    except Exception as e:
        messages.error(request, f'خطا در بارگذاری پروفایل اجتماعی: {str(e)}')
        return redirect('social_home')

@login_required
def edit_social_profile(request):
    try:
        social_profile, created = SocialProfile.objects.get_or_create(user=request.user)
        
        if request.method == 'POST':
            form = SocialProfileForm(request.POST, instance=social_profile)
            if form.is_valid():
                form.save()
                messages.success(request, 'پروفایل با موفقیت به‌روزرسانی شد')
                return redirect('social_profile')
        else:
            form = SocialProfileForm(instance=social_profile)
        
        user_age_group = request.user.age_group
        age_group_settings = AgeGroupSettings.objects.filter(
            age_group=user_age_group, is_active=True
        ).first()
        
        return render(request, 'social/edit_profile.html', {
            'form': form,
            'social_profile': social_profile,
            'user_age_group': user_age_group,
            'age_group_settings': age_group_settings,
        })
    except Exception as e:
        messages.error(request, f'خطا در ویرایش پروفایل: {str(e)}')
        return redirect('social_profile')

@login_required
def create_post(request):
    try:
        if request.method == 'POST':
            form = PostForm(request.POST, request.FILES)
            if form.is_valid():
                post = form.save(commit=False)
                post.user = request.user
                
                if post.image:
                    post.content_type = 'image'
                elif post.video:
                    post.content_type = 'video'
                elif post.audio:
                    post.content_type = 'audio'
                else:
                    post.content_type = 'text'
                
                post.save()
                
                social_profile, created = SocialProfile.objects.get_or_create(user=request.user)
                social_profile.posts_count = Post.objects.filter(user=request.user, is_active=True).count()
                social_profile.save()
                
                messages.success(request, 'پست با موفقیت منتشر شد')
                return redirect('social_profile')
        else:
            form = PostForm()
        
        user_age_group = request.user.age_group
        age_group_settings = AgeGroupSettings.objects.filter(
            age_group=user_age_group, is_active=True
        ).first()
        
        return render(request, 'social/create_post.html', {
            'form': form,
            'user_age_group': user_age_group,
            'age_group_settings': age_group_settings,
        })
    except Exception as e:
        messages.error(request, f'خطا در ایجاد پست: {str(e)}')
        return redirect('social_home')

@login_required
def post_detail(request, post_id):
    try:
        post = get_object_or_404(Post, id=post_id, is_active=True)
        comments = Comment.objects.filter(
            post=post, is_active=True, parent__isnull=True
        ).select_related('user')
        
        if post.user != request.user:
            social_profile = SocialProfile.objects.get(user=post.user)
            if social_profile.is_private:
                is_following = Follow.objects.filter(follower=request.user, following=post.user).exists()
                if not is_following:
                    messages.error(request, 'این حساب خصوصی است و باید آن را دنبال کنید')
                    return redirect('social_profile', user_id=post.user.id)
        
        user_age_group = request.user.age_group
        age_group_settings = AgeGroupSettings.objects.filter(
            age_group=user_age_group, is_active=True
        ).first()
        
        return render(request, 'social/post_detail.html', {
            'post': post,
            'comments': comments,
            'comment_form': CommentForm(),
            'is_liked': PostLike.objects.filter(user=request.user, post=post).exists(),
            'user_age_group': user_age_group,
            'age_group_settings': age_group_settings,
        })
    except Exception as e:
        messages.error(request, f'خطا در بارگذاری پست: {str(e)}')
        return redirect('social_home')

@login_required
def create_story(request):
    try:
        if request.method == 'POST':
            form = StoryForm(request.POST, request.FILES)
            if form.is_valid():
                story = form.save(commit=False)
                story.user = request.user
                
                if story.image:
                    story.content_type = 'image'
                elif story.video:
                    story.content_type = 'video'
                else:
                    messages.error(request, 'لطفاً یک عکس یا ویدیو انتخاب کنید')
                    return render(request, 'social/create_story.html', {'form': form})
                
                story.save()
                messages.success(request, 'استوری با موفقیت منتشر شد')
                return redirect('social_home')
        else:
            form = StoryForm()
        
        user_age_group = request.user.age_group
        age_group_settings = AgeGroupSettings.objects.filter(
            age_group=user_age_group, is_active=True
        ).first()
        
        return render(request, 'social/create_story.html', {
            'form': form,
            'user_age_group': user_age_group,
            'age_group_settings': age_group_settings,
        })
    except Exception as e:
        messages.error(request, f'خطا در ایجاد استوری: {str(e)}')
        return redirect('social_home')

@login_required
def story_view(request, story_id):
    try:
        story = get_object_or_404(
            Story, id=story_id, is_active=True, expires_at__gt=timezone.now()
        )
        
        if story.user != request.user:
            social_profile = SocialProfile.objects.get(user=story.user)
            if social_profile.is_private:
                is_following = Follow.objects.filter(follower=request.user, following=story.user).exists()
                if not is_following:
                    messages.error(request, 'این حساب خصوصی است و باید آن را دنبال کنید')
                    return redirect('social_profile', user_id=story.user.id)
        
        StoryView.objects.get_or_create(story=story, user=request.user)
        story.views_count = StoryView.objects.filter(story=story).count()
        story.save()
        
        user_stories = Story.objects.filter(
            user=story.user, is_active=True, expires_at__gt=timezone.now()
        ).order_by('created_at')
        
        user_age_group = request.user.age_group
        age_group_settings = AgeGroupSettings.objects.filter(
            age_group=user_age_group, is_active=True
        ).first()
        
        return render(request, 'social/story_view.html', {
            'story': story,
            'user_stories': user_stories,
            'current_story_index': list(user_stories).index(story),
            'user_age_group': user_age_group,
            'age_group_settings': age_group_settings,
        })
    except Exception as e:
        messages.error(request, f'خطا در بارگذاری استوری: {str(e)}')
        return redirect('social_home')

@login_required
def follow_user(request, user_id):
    try:
        user_to_follow = get_object_or_404(CustomUser, id=user_id)
        
        if request.user == user_to_follow:
            messages.error(request, 'شما نمی‌توانید خودتان را دنبال کنید')
            return redirect('social_profile', user_id=user_id)
        
        social_profile = SocialProfile.objects.get(user=user_to_follow)
        
        if Follow.objects.filter(follower=request.user, following=user_to_follow).exists():
            messages.info(request, f'شما قبلاً {user_to_follow.get_full_name()} را دنبال می‌کنید')
            return redirect('social_profile', user_id=user_id)
        
        if social_profile.is_private:
            existing_request = FollowRequest.objects.filter(
                from_user=request.user, to_user=user_to_follow
            ).first()
            
            if existing_request:
                if existing_request.is_accepted:
                    messages.info(request, 'درخواست شما قبلاً پذیرفته شده است')
                else:
                    messages.info(request, 'درخواست دنبال کردن قبلاً ارسال شده و در انتظار تایید است')
            else:
                FollowRequest.objects.create(from_user=request.user, to_user=user_to_follow)
                messages.success(request, 'درخواست دنبال کردن ارسال شد')
        else:
            Follow.objects.create(follower=request.user, following=user_to_follow)
            update_follow_counts(request.user, user_to_follow)
            messages.success(request, f'شما {user_to_follow.get_full_name()} را دنبال کردید')
        
        return redirect('social_profile', user_id=user_id)
    except Exception as e:
        messages.error(request, f'خطا در دنبال کردن کاربر: {str(e)}')
        return redirect('social_home')

@login_required
def unfollow_user(request, user_id):
    try:
        user_to_unfollow = get_object_or_404(CustomUser, id=user_id)
        
        follow = Follow.objects.filter(follower=request.user, following=user_to_unfollow).first()
        if follow:
            follow.delete()
            update_follow_counts(request.user, user_to_unfollow)
            messages.success(request, f'شما {user_to_unfollow.get_full_name()} را دنبال نمی‌کنید')
        else:
            messages.info(request, f'شما {user_to_unfollow.get_full_name()} را دنبال نمی‌کردید')
        
        FollowRequest.objects.filter(from_user=request.user, to_user=user_to_unfollow).delete()
        
        return redirect('social_profile', user_id=user_id)
    except Exception as e:
        messages.error(request, f'خطا در لغو دنبال کردن: {str(e)}')
        return redirect('social_home')

@login_required
def like_post(request, post_id):
    try:
        if request.method != 'POST':
            return JsonResponse({'success': False, 'error': 'درخواست نامعتبر'})
        
        post = get_object_or_404(Post, id=post_id, is_active=True)
        
        like, created = PostLike.objects.get_or_create(user=request.user, post=post)
        
        if not created:
            like.delete()
        
        post.likes_count = PostLike.objects.filter(post=post).count()
        post.save()
        
        return JsonResponse({
            'success': True,
            'action': 'liked' if created else 'unliked',
            'likes_count': post.likes_count
        })
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})

@login_required
def add_comment(request, post_id):
    try:
        if request.method != 'POST':
            return JsonResponse({'success': False, 'error': 'درخواست نامعتبر'})
        
        post = get_object_or_404(Post, id=post_id, is_active=True)
        form = CommentForm(request.POST)
        
        if form.is_valid():
            comment = form.save(commit=False)
            comment.user = request.user
            comment.post = post
            comment.save()
            
            post.comments_count = Comment.objects.filter(post=post, is_active=True).count()
            post.save()
            
            return JsonResponse({
                'success': True,
                'comment_id': comment.id,
                'user_name': comment.user.get_full_name(),
                'text': comment.text,
                'created_at': comment.created_at.strftime('%Y-%m-%d %H:%M'),
            })
        
        return JsonResponse({'success': False, 'error': 'خطا در ثبت نظر'})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})

@login_required
def follow_requests(request):
    try:
        if not request.user.social_profile.is_private:
            messages.info(request, 'حساب شما عمومی است و درخواست دنبال کردن ندارد')
            return redirect('social_profile')
        
        requests_list = FollowRequest.objects.filter(
            to_user=request.user, is_accepted=False
        ).select_related('from_user')
        
        user_age_group = request.user.age_group
        age_group_settings = AgeGroupSettings.objects.filter(
            age_group=user_age_group, is_active=True
        ).first()
        
        return render(request, 'social/follow_requests.html', {
            'requests': requests_list,
            'user_age_group': user_age_group,
            'age_group_settings': age_group_settings,
        })
    except Exception as e:
        messages.error(request, f'خطا در بارگذاری درخواست‌ها: {str(e)}')
        return redirect('social_profile')

@login_required
def handle_follow_request(request, request_id, action):
    try:
        follow_request = get_object_or_404(
            FollowRequest, id=request_id, to_user=request.user
        )
        
        if action == 'accept':
            Follow.objects.create(
                follower=follow_request.from_user,
                following=request.user
            )
            follow_request.is_accepted = True
            follow_request.save()
            update_follow_counts(follow_request.from_user, request.user)
            messages.success(request, f'درخواست {follow_request.from_user.get_full_name()} پذیرفته شد')
        elif action == 'reject':
            follow_request.delete()
            messages.success(request, f'درخواست {follow_request.from_user.get_full_name()} رد شد')
        
        return redirect('follow_requests')
    except Exception as e:
        messages.error(request, f'خطا در مدیریت درخواست: {str(e)}')
        return redirect('follow_requests')

def update_follow_counts(follower_user, following_user):
    try:
        follower_profile, _ = SocialProfile.objects.get_or_create(user=follower_user)
        following_profile, _ = SocialProfile.objects.get_or_create(user=following_user)
        
        follower_profile.following_count = Follow.objects.filter(follower=follower_user).count()
        follower_profile.save()
        
        following_profile.followers_count = Follow.objects.filter(following=following_user).count()
        following_profile.save()
    except Exception as e:
        print(f"خطا در به‌روزرسانی تعداد دنبال‌کنندگان: {str(e)}")

@login_required
def remove_profile_image(request):
    try:
        if request.method == 'POST':
            user = request.user
            if user.profile_image:
                user.profile_image.delete(save=False)
                user.profile_image = None
                user.save()
                return JsonResponse({'success': True})
            return JsonResponse({'success': False, 'error': 'عکس پروفایل وجود ندارد'})
        return JsonResponse({'success': False, 'error': 'درخواست نامعتبر'})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})

def map(request):
    try:
        user_age_group = request.user.age_group if request.user.is_authenticated else None
        age_group_settings = AgeGroupSettings.objects.filter(
            age_group=user_age_group, is_active=True
        ).first() if user_age_group else None
        
        return render(request, 'map.html', {
            'user_age_group': user_age_group,
            'age_group_settings': age_group_settings,
        })
    except Exception as e:
        messages.error(request, f'خطا در بارگذاری صفحه نقشه: {str(e)}')
        return render(request, 'map.html', {})

def test_gmail(request):
    try:
        send_mail(
            'تست Gmail از پلتفرم مهدوی',
            'اگر این ایمیل را دریافت کردید، سیستم Gmail کار می‌کند!',
            settings.DEFAULT_FROM_EMAIL,
            [settings.DEFAULT_FROM_EMAIL],
            fail_silently=False,
        )
        return JsonResponse({'status': 'ایمیل ارسال شد! Gmail کار می‌کند.'})
    except Exception as e:
        return JsonResponse({'status': 'خطا', 'error': str(e)})

def test_register_simple(request):
    try:
        if request.method == 'POST':
            try:
                user = CustomUser.objects.create_user(
                    first_name=request.POST.get('first_name', 'تست'),
                    last_name=request.POST.get('last_name', 'کاربر'),
                    phone=request.POST.get('phone', '09123456789'),
                    email=request.POST.get('email', 'test@example.com'),
                    age=int(request.POST.get('age', 25)),
                    password=request.POST.get('password', '1234')
                )
                messages.success(request, f'کاربر تست با موفقیت ایجاد شد: {user}')
                return redirect('login')
            except Exception as e:
                messages.error(request, f'خطا: {str(e)}')
        
        return render(request, 'test_register.html')
    except Exception as e:
        messages.error(request, f'خطا در تست ثبت نام: {str(e)}')
        return render(request, 'test_register.html')

def library_home(request):
    try:
        categories = BookCategory.objects.filter(is_active=True)
        featured_books = Book.objects.filter(
            is_active=True, status='published', is_featured=True
        ).order_by('-created_at')[:8]
        
        new_books = Book.objects.filter(
            is_active=True, status='published'
        ).order_by('-created_at')[:8]
        
        user_age_group = request.user.age_group if request.user.is_authenticated else None
        age_group_settings = AgeGroupSettings.objects.filter(
            age_group=user_age_group, is_active=True
        ).first() if user_age_group else None
        
        cart_count = BookOrder.objects.filter(
            user=request.user, status='pending'
        ).count() if request.user.is_authenticated else 0
        
        return render(request, 'library/library_home.html', {
            'categories': categories,
            'featured_books': featured_books,
            'new_books': new_books,
            'user_age_group': user_age_group,
            'age_group_settings': age_group_settings,
            'cart_count': cart_count,
        })
    except Exception as e:
        messages.error(request, f'خطا در بارگذاری صفحه کتابخانه: {str(e)}')
        return render(request, 'library/library_home.html', {})

def book_list(request):
    try:
        category_id = request.GET.get('category')
        search_query = request.GET.get('q', '')
        book_type = request.GET.get('type', '')
        sort_by = request.GET.get('sort', 'newest')
        
        user_age_group = request.user.age_group if request.user.is_authenticated else None
        
        books = Book.objects.filter(is_active=True, status='published')
        
        if category_id:
            books = books.filter(category_id=category_id)
        
        if search_query:
            books = books.filter(
                Q(title__icontains=search_query) | Q(author__icontains=search_query) |
                Q(description__icontains=search_query)
            )
        
        if book_type:
            books = books.filter(book_type=book_type)
        
        sort_options = {
            'title': 'title',
            'author': 'author',
            'newest': '-created_at'
        }
        books = books.order_by(sort_options.get(sort_by, '-created_at'))
        
        categories = BookCategory.objects.filter(is_active=True)
        
        age_group_settings = AgeGroupSettings.objects.filter(
            age_group=user_age_group, is_active=True
        ).first() if user_age_group else None
        
        return render(request, 'library/book_list.html', {
            'books': books,
            'categories': categories,
            'selected_category': category_id,
            'search_query': search_query,
            'book_type': book_type,
            'sort_by': sort_by,
            'user_age_group': user_age_group,
            'age_group_settings': age_group_settings,
        })
    except Exception as e:
        messages.error(request, f'خطا در بارگذاری لیست کتاب‌ها: {str(e)}')
        return redirect('library_home')

def book_detail(request, book_id):
    try:
        book = get_object_or_404(Book, id=book_id, is_active=True, status='published')
        
        user_age_group = request.user.age_group if request.user.is_authenticated else None
        
        has_access = False
        user_order = None
        
        if request.user.is_authenticated:
            user_access = UserBookAccess.objects.filter(
                user=request.user, book=book, is_active=True
            ).first()
            
            if user_access and user_access.can_access:
                has_access = True
            
            user_order = BookOrder.objects.filter(
                user=request.user, book=book
            ).order_by('-created_at').first()
        
        related_books = Book.objects.filter(
            category=book.category, is_active=True, status='published'
        ).exclude(id=book.id).order_by('?')[:4]
        
        age_group_settings = AgeGroupSettings.objects.filter(
            age_group=user_age_group, is_active=True
        ).first() if user_age_group else None
        
        return render(request, 'library/book_detail.html', {
            'book': book,
            'related_books': related_books,
            'has_access': has_access,
            'user_order': user_order,
            'user_age_group': user_age_group,
            'age_group_settings': age_group_settings,
        })
    except Exception as e:
        messages.error(request, f'خطا در بارگذاری کتاب: {str(e)}')
        return redirect('library_home')

@login_required
def add_book_to_cart(request, book_id):
    try:
        if request.method != 'POST':
            return redirect('book_detail', book_id=book_id)
        
        book = get_object_or_404(Book, id=book_id, is_active=True, status='published')
        
        if UserBookAccess.objects.filter(user=request.user, book=book, is_active=True).exists():
            messages.info(request, 'شما قبلاً این کتاب را خریداری کرده‌اید')
            return redirect('book_detail', book_id=book_id)
        
        if book.is_free:
            messages.error(request, 'این کتاب رایگان است و نیازی به خرید ندارد')
            return redirect('book_detail', book_id=book_id)
        
        if BookOrder.objects.filter(user=request.user, book=book, status='pending').exists():
            messages.info(request, 'این کتاب قبلاً به سبد خرید شما اضافه شده است')
            return redirect('book_detail', book_id=book_id)
        
        BookOrder.objects.create(
            user=request.user,
            book=book,
            unit_price=book.final_price,
            total_amount=book.final_price,
            status='pending'
        )
        
        messages.success(request, 'کتاب به سبد خرید اضافه شد')
        return redirect('book_cart')
    except Exception as e:
        messages.error(request, f'خطا در افزودن به سبد خرید: {str(e)}')
        return redirect('book_detail', book_id=book_id)

@login_required
def book_cart(request):
    try:
        orders = BookOrder.objects.filter(
            user=request.user, status='pending'
        ).select_related('book')
        
        total_amount = sum(order.total_amount for order in orders)
        
        user_age_group = request.user.age_group
        age_group_settings = AgeGroupSettings.objects.filter(
            age_group=user_age_group, is_active=True
        ).first()
        
        return render(request, 'library/book_cart.html', {
            'orders': orders,
            'total_amount': total_amount,
            'user_age_group': user_age_group,
            'age_group_settings': age_group_settings,
        })
    except Exception as e:
        messages.error(request, f'خطا در بارگذاری سبد خرید: {str(e)}')
        return redirect('library_home')

@login_required
def remove_book_from_cart(request, order_id):
    try:
        order = get_object_or_404(BookOrder, id=order_id, user=request.user, status='pending')
        order.delete()
        messages.success(request, 'سفارش از سبد خرید حذف شد')
        return redirect('book_cart')
    except Exception as e:
        messages.error(request, f'خطا در حذف از سبد خرید: {str(e)}')
        return redirect('book_cart')

@login_required
def book_checkout(request):
    try:
        orders = BookOrder.objects.filter(user=request.user, status='pending')
        
        if not orders.exists():
            messages.error(request, 'سبد خرید شما خالی است')
            return redirect('book_cart')
        
        total_amount = sum(order.total_amount for order in orders)
        
        if request.method == 'POST':
            form = BookPaymentForm(request.POST, request.FILES)
            if form.is_valid():
                for order in orders:
                    order.payment_receipt = form.cleaned_data['payment_receipt']
                    order.payment_date = timezone.now()
                    order.status = 'paid'
                    order.save()
                
                messages.success(request, 'رسید پرداخت با موفقیت آپلود شد. پس از تایید ادمین، دسترسی شما فعال خواهد شد.')
                return redirect('book_orders')
        else:
            form = BookPaymentForm()
        
        user_age_group = request.user.age_group
        age_group_settings = AgeGroupSettings.objects.filter(
            age_group=user_age_group, is_active=True
        ).first()
        
        return render(request, 'library/book_checkout.html', {
            'orders': orders,
            'total_amount': total_amount,
            'form': form,
            'your_card_number': "6037-XXXX-XXXX-XXXX",
            'user_age_group': user_age_group,
            'age_group_settings': age_group_settings,
        })
    except Exception as e:
        messages.error(request, f'خطا در پردازش پرداخت: {str(e)}')
        return redirect('book_cart')

@login_required
def book_orders(request):
    try:
        orders = BookOrder.objects.filter(user=request.user).order_by('-created_at')
        
        user_age_group = request.user.age_group
        age_group_settings = AgeGroupSettings.objects.filter(
            age_group=user_age_group, is_active=True
        ).first()
        
        return render(request, 'library/book_orders.html', {
            'orders': orders,
            'user_age_group': user_age_group,
            'age_group_settings': age_group_settings,
        })
    except Exception as e:
        messages.error(request, f'خطا در بارگذاری تاریخچه سفارش‌ها: {str(e)}')
        return redirect('library_home')

@login_required
def download_book(request, book_id):
    try:
        book = get_object_or_404(Book, id=book_id)
        
        user_access = UserBookAccess.objects.filter(
            user=request.user, book=book, is_active=True
        ).first()
        
        if not user_access and not book.is_free:
            messages.error(request, 'شما دسترسی به این کتاب را ندارید')
            return redirect('book_detail', book_id=book_id)
        
        if not book.is_free and not user_access:
            messages.error(request, 'برای دانلود این کتاب باید آن را خریداری کنید')
            return redirect('book_detail', book_id=book_id)
        
        if book.is_free and not user_access:
            UserBookAccess.objects.create(
                user=request.user, book=book, order=None, is_active=True
            )
        
        return FileResponse(book.pdf_file, as_attachment=True, filename=f"{book.title}.pdf")
    except Exception as e:
        messages.error(request, f'خطا در دانلود کتاب: {str(e)}')
        return redirect('book_detail', book_id=book_id)

@login_required
def book_reader(request, book_id):
    try:
        book = get_object_or_404(Book, id=book_id)
        
        user_access = UserBookAccess.objects.filter(
            user=request.user, book=book, is_active=True
        ).first()
        
        if not user_access and not book.is_free:
            messages.error(request, 'شما دسترسی به این کتاب را ندارید')
            return redirect('book_detail', book_id=book_id)
        
        if book.is_free and not user_access:
            user_access = UserBookAccess.objects.create(
                user=request.user, book=book, order=None, is_active=True
            )
        
        user_age_group = request.user.age_group
        age_group_settings = AgeGroupSettings.objects.filter(
            age_group=user_age_group, is_active=True
        ).first()
        
        return render(request, 'library/book_reader.html', {
            'book': book,
            'user_access': user_access,
            'user_age_group': user_age_group,
            'age_group_settings': age_group_settings,
        })
    except Exception as e:
        messages.error(request, f'خطا در بارگذاری کتابخوان: {str(e)}')
        return redirect('book_detail', book_id=book_id)

@login_required
def library_management(request):
    try:
        if not request.user.is_superuser:
            messages.error(request, 'شما دسترسی به این بخش را ندارید')
            return redirect('library_home')
        
        total_books = Book.objects.count()
        total_categories = BookCategory.objects.count()
        pending_orders = BookOrder.objects.filter(status='paid').count()
        total_orders = BookOrder.objects.count()
        recent_orders = BookOrder.objects.all().order_by('-created_at')[:5]
        
        return render(request, 'library/admin/library_management.html', {
            'total_books': total_books,
            'total_categories': total_categories,
            'pending_orders': pending_orders,
            'total_orders': total_orders,
            'recent_orders': recent_orders,
        })
    except Exception as e:
        messages.error(request, f'خطا در بارگذاری مدیریت کتابخانه: {str(e)}')
        return redirect('library_home')

@login_required
def book_management(request):
    try:
        if not request.user.is_superuser:
            messages.error(request, 'شما دسترسی به این بخش را ندارید')
            return redirect('library_home')
        
        if request.method == 'POST':
            form = BookForm(request.POST, request.FILES)
            if form.is_valid():
                form.save()
                messages.success(request, 'کتاب با موفقیت اضافه شد')
                return redirect('book_management')
        else:
            form = BookForm()
        
        books = Book.objects.all().order_by('-created_at')
        
        return render(request, 'library/admin/book_management.html', {
            'form': form,
            'books': books,
        })
    except Exception as e:
        messages.error(request, f'خطا در مدیریت کتاب‌ها: {str(e)}')
        return redirect('library_management')

@login_required
def book_category_management(request):
    try:
        if not request.user.is_superuser:
            messages.error(request, 'شما دسترسی به این بخش را ندارید')
            return redirect('library_home')
        
        if request.method == 'POST':
            form = BookCategoryForm(request.POST)
            if form.is_valid():
                form.save()
                messages.success(request, 'دسته‌بندی با موفقیت اضافه شد')
                return redirect('book_category_management')
        else:
            form = BookCategoryForm()
        
        categories = BookCategory.objects.all().order_by('order')
        
        return render(request, 'library/admin/category_management.html', {
            'form': form,
            'categories': categories,
        })
    except Exception as e:
        messages.error(request, f'خطا در مدیریت دسته‌بندی‌ها: {str(e)}')
        return redirect('library_management')

@login_required
def book_order_management(request):
    try:
        if not request.user.is_superuser:
            messages.error(request, 'شما دسترسی به این بخش را ندارید')
            return redirect('library_home')
        
        status_filter = request.GET.get('status', 'all')
        orders = BookOrder.objects.all().select_related('user', 'book').order_by('-created_at')
        
        if status_filter != 'all':
            orders = orders.filter(status=status_filter)
        
        return render(request, 'library/admin/order_management.html', {
            'orders': orders,
            'status_filter': status_filter,
        })
    except Exception as e:
        messages.error(request, f'خطا در مدیریت سفارش‌ها: {str(e)}')
        return redirect('library_management')

@login_required
def approve_book_order(request, order_id):
    try:
        if not request.user.is_superuser:
            messages.error(request, 'شما دسترسی به این بخش را ندارید')
            return redirect('book_order_management')
        
        order = get_object_or_404(BookOrder, id=order_id)
        
        if order.status != 'paid':
            messages.error(request, 'فقط سفارش‌های پرداخت شده قابل تایید هستند')
            return redirect('book_order_management')
        
        UserBookAccess.objects.filter(user=order.user, book=order.book).update(is_active=False)
        
        UserBookAccess.objects.create(
            user=order.user, book=order.book, order=order, is_active=True
        )
        
        order.status = 'approved'
        order.save()
        
        messages.success(request, f'سفارش {order.order_number} تایید شد و دسترسی کاربر فعال گردید')
        return redirect('book_order_management')
    except Exception as e:
        messages.error(request, f'خطا در تایید سفارش: {str(e)}')
        return redirect('book_order_management')

@login_required
def reject_book_order(request, order_id):
    try:
        if not request.user.is_superuser:
            messages.error(request, 'شما دسترسی به این بخش را ندارید')
            return redirect('book_order_management')
        
        order = get_object_or_404(BookOrder, id=order_id)
        
        if request.method == 'POST':
            order.admin_notes = request.POST.get('admin_notes', '')
            order.status = 'rejected'
            order.save()
            messages.success(request, f'سفارش {order.order_number} رد شد')
        
        return redirect('book_order_management')
    except Exception as e:
        messages.error(request, f'خطا در رد سفارش: {str(e)}')
        return redirect('book_order_management')

def virtual_tours_home(request):
    try:
        categories = VirtualTourCategory.objects.filter(is_active=True).order_by('order')
        
        tours = VirtualTour.objects.filter(
            status='published', is_active=True
        ).select_related('category').order_by('order', '-created_at')
        
        category_id = request.GET.get('category')
        if category_id:
            tours = tours.filter(category_id=category_id)
        
        featured = request.GET.get('featured')
        if featured:
            tours = tours.filter(is_featured=True)
        
        featured_tours = tours.filter(is_featured=True)[:6]
        
        return render(request, 'virtual_tours/home.html', {
            'categories': categories,
            'tours': tours,
            'featured_tours': featured_tours,
            'selected_category': category_id,
            'total_tours': tours.count(),
        })
    except Exception as e:
        messages.error(request, f'خطا در بارگذاری تورهای مجازی: {str(e)}')
        return render(request, 'virtual_tours/home.html', {})

def virtual_tour_view(request, tour_id):
    try:
        tour = get_object_or_404(VirtualTour, id=tour_id, status='published', is_active=True)
        
        tour.increment_view_count()
        
        related_tours = VirtualTour.objects.filter(
            category=tour.category, status='published', is_active=True
        ).exclude(id=tour.id).order_by('?')[:4]
        
        return render(request, 'virtual_tours/tour_view.html', {
            'tour': tour,
            'related_tours': related_tours,
        })
    except Exception as e:
        messages.error(request, f'خطا در بارگذاری تور مجازی: {str(e)}')
        return redirect('virtual_tours_home')

@login_required
def virtual_tour_management(request):
    try:
        if not request.user.is_superuser:
            messages.error(request, 'شما دسترسی به این بخش را ندارید')
            return redirect('virtual_tours_home')
        
        if request.method == 'POST':
            form = VirtualTourForm(request.POST, request.FILES)
            if form.is_valid():
                form.save()
                messages.success(request, 'تور مجازی با موفقیت اضافه شد')
                return redirect('virtual_tour_management')
        else:
            form = VirtualTourForm()
        
        tours = VirtualTour.objects.all().select_related('category').order_by('order', '-created_at')
        
        return render(request, 'virtual_tours/management.html', {
            'form': form,
            'tours': tours,
        })
    except Exception as e:
        messages.error(request, f'خطا در مدیریت تورهای مجازی: {str(e)}')
        return redirect('virtual_tours_home')

@login_required
def virtual_tour_category_management(request):
    try:
        if not request.user.is_superuser:
            messages.error(request, 'شما دسترسی به این بخش را ندارید')
            return redirect('virtual_tours_home')
        
        if request.method == 'POST':
            form = VirtualTourCategoryForm(request.POST)
            if form.is_valid():
                form.save()
                messages.success(request, 'دسته‌بندی با موفقیت اضافه شد')
                return redirect('virtual_tour_category_management')
        else:
            form = VirtualTourCategoryForm()
        
        categories = VirtualTourCategory.objects.all().order_by('order')
        
        return render(request, 'virtual_tours/category_management.html', {
            'form': form,
            'categories': categories,
        })
    except Exception as e:
        messages.error(request, f'خطا در مدیریت دسته‌بندی‌ها: {str(e)}')
        return redirect('virtual_tours_home')

@login_required
def delete_virtual_tour(request, tour_id):
    try:
        if not request.user.is_superuser:
            messages.error(request, 'شما دسترسی به این بخش را ندارید')
            return redirect('virtual_tour_management')
        
        tour = get_object_or_404(VirtualTour, id=tour_id)
        tour_title = tour.title
        tour.delete()
        
        messages.success(request, f'تور "{tour_title}" با موفقیت حذف شد')
        return redirect('virtual_tour_management')
    except Exception as e:
        messages.error(request, f'خطا در حذف تور: {str(e)}')
        return redirect('virtual_tour_management')

@login_required
def delete_virtual_tour_category(request, category_id):
    try:
        if not request.user.is_superuser:
            messages.error(request, 'شما دسترسی به این بخش را ندارید')
            return redirect('virtual_tour_category_management')
        
        category = get_object_or_404(VirtualTourCategory, id=category_id)
        
        if category.tours.exists():
            messages.error(request, 'امکان حذف دسته‌بندی دارای تور وجود ندارد')
            return redirect('virtual_tour_category_management')
        
        category_name = category.name
        category.delete()
        
        messages.success(request, f'دسته‌بندی "{category_name}" با موفقیت حذف شد')
        return redirect('virtual_tour_category_management')
    except Exception as e:
        messages.error(request, f'خطا در حذف دسته‌بندی: {str(e)}')
        return redirect('virtual_tour_category_management')

def charity_home(request):
    try:
        categories = CharityCategory.objects.filter(is_active=True).order_by('order')
        
        active_projects = CharityProject.objects.filter(
            status='active', is_active=True
        ).order_by('-created_at')
        
        featured_projects = CharityProject.objects.filter(
            is_featured=True, is_active=True, status='active'
        ).order_by('-created_at')[:6]
        
        urgent_projects = CharityProject.objects.filter(
            is_urgent=True, is_active=True, status='active'
        ).order_by('-created_at')[:3]
        
        total_projects = CharityProject.objects.filter(is_active=True).count()
        total_donations = CharityDonation.objects.filter(status='completed').count()
        total_amount = CharityDonation.objects.filter(status='completed').aggregate(
            total=Sum('amount')
        )['total'] or 0
        
        user_age_group = request.user.age_group if request.user.is_authenticated else None
        age_group_settings = AgeGroupSettings.objects.filter(
            age_group=user_age_group, is_active=True
        ).first() if user_age_group else None
        
        return render(request, 'charity/charity_home.html', {
            'categories': categories,
            'active_projects': active_projects,
            'featured_projects': featured_projects,
            'urgent_projects': urgent_projects,
            'total_projects': total_projects,
            'total_donations': total_donations,
            'total_amount': total_amount,
            'user_age_group': user_age_group,
            'age_group_settings': age_group_settings,
        })
    except Exception as e:
        messages.error(request, f'خطا در بارگذاری صفحه خیریه: {str(e)}')
        return render(request, 'charity/charity_home.html', {})

def charity_projects(request):
    try:
        category_id = request.GET.get('category')
        status_filter = request.GET.get('status', 'active')
        sort_by = request.GET.get('sort', 'newest')
        
        projects = CharityProject.objects.filter(is_active=True)
        
        if category_id:
            projects = projects.filter(category_id=category_id)
        
        if status_filter != 'all':
            projects = projects.filter(status=status_filter)
        
        if sort_by == 'progress':
            projects = projects.annotate(
                progress=models.F('current_amount') / models.F('target_amount') * 100
            ).order_by('-progress', '-created_at')
        elif sort_by == 'urgent':
            projects = projects.filter(is_urgent=True).order_by('-created_at')
        elif sort_by == 'featured':
            projects = projects.filter(is_featured=True).order_by('-created_at')
        elif sort_by == 'ending':
            projects = projects.filter(end_date__isnull=False).order_by('end_date')
        else:
            projects = projects.order_by('-created_at')
        
        categories = CharityCategory.objects.filter(is_active=True).order_by('order')
        
        user_age_group = request.user.age_group if request.user.is_authenticated else None
        age_group_settings = AgeGroupSettings.objects.filter(
            age_group=user_age_group, is_active=True
        ).first() if user_age_group else None
        
        return render(request, 'charity/projects_list.html', {
            'projects': projects,
            'categories': categories,
            'selected_category': category_id,
            'status_filter': status_filter,
            'sort_by': sort_by,
            'user_age_group': user_age_group,
            'age_group_settings': age_group_settings,
        })
    except Exception as e:
        messages.error(request, f'خطا در بارگذاری لیست پروژه‌ها: {str(e)}')
        return redirect('charity_home')

def charity_project_detail(request, project_id):
    try:
        project = get_object_or_404(CharityProject, id=project_id, is_active=True)
        
        gallery_images = project.images.all().order_by('order')
        updates = project.updates.all().order_by('-created_at')
        recent_donations = project.donations.filter(
            status='completed'
        ).select_related('user').order_by('-created_at')[:10]
        volunteers = project.volunteers.filter(status='active').select_related('user')
        
        user_donation = None
        if request.user.is_authenticated:
            user_donation = CharityDonation.objects.filter(
                user=request.user, project=project
            ).order_by('-created_at').first()
        
        user_age_group = request.user.age_group if request.user.is_authenticated else None
        age_group_settings = AgeGroupSettings.objects.filter(
            age_group=user_age_group, is_active=True
        ).first() if user_age_group else None
        
        return render(request, 'charity/project_detail.html', {
            'project': project,
            'gallery_images': gallery_images,
            'updates': updates,
            'recent_donations': recent_donations,
            'volunteers': volunteers,
            'user_donation': user_donation,
            'donation_form': CharityDonationForm(),
            'user_age_group': user_age_group,
            'age_group_settings': age_group_settings,
        })
    except Exception as e:
        messages.error(request, f'خطا در بارگذاری پروژه: {str(e)}')
        return redirect('charity_projects')

@login_required
def make_donation(request, project_id):
    try:
        project = get_object_or_404(CharityProject, id=project_id, is_active=True, status='active')
        
        if request.method == 'POST':
            form = CharityDonationForm(request.POST)
            if form.is_valid():
                donation = form.save(commit=False)
                donation.user = request.user
                donation.project = project
                donation.save()
                messages.success(request, 'کمک شما ثبت شد. لطفاً پرداخت خود را انجام دهید.')
                return redirect('charity_payment', donation_id=donation.id)
        else:
            form = CharityDonationForm()
        
        user_age_group = request.user.age_group
        age_group_settings = AgeGroupSettings.objects.filter(
            age_group=user_age_group, is_active=True
        ).first()
        
        return render(request, 'charity/make_donation.html', {
            'project': project,
            'form': form,
            'suggested_amounts': [10000, 50000, 100000, 500000, 1000000],
            'user_age_group': user_age_group,
            'age_group_settings': age_group_settings,
        })
    except Exception as e:
        messages.error(request, f'خطا در ثبت کمک: {str(e)}')
        return redirect('charity_project_detail', project_id=project_id)

@login_required
def charity_payment(request, donation_id):
    try:
        donation = get_object_or_404(CharityDonation, id=donation_id, user=request.user)
        project = donation.project
        
        if donation.status != 'pending':
            messages.info(request, 'این کمک قبلاً پرداخت شده است')
            return redirect('charity_project_detail', project_id=project.id)
        
        if request.method == 'POST':
            form = CharityPaymentForm(request.POST, request.FILES, instance=donation)
            if form.is_valid():
                donation = form.save(commit=False)
                donation.payment_date = timezone.now()
                donation.status = 'paid'
                donation.save()
                messages.success(request, 'رسید پرداخت با موفقیت آپلود شد. پس از تایید ادمین، کمک شما نهایی خواهد شد.')
                return redirect('charity_donations')
        else:
            form = CharityPaymentForm(instance=donation)
        
        user_age_group = request.user.age_group
        age_group_settings = AgeGroupSettings.objects.filter(
            age_group=user_age_group, is_active=True
        ).first()
        
        return render(request, 'charity/payment.html', {
            'donation': donation,
            'project': project,
            'form': form,
            'card_number': project.card_number,
            'card_holder': project.card_holder,
            'bank_name': project.bank_name,
            'user_age_group': user_age_group,
            'age_group_settings': age_group_settings,
        })
    except Exception as e:
        messages.error(request, f'خطا در پردازش پرداخت: {str(e)}')
        return redirect('charity_project_detail', project_id=project_id)

@login_required
def charity_donations(request):
    try:
        donations = CharityDonation.objects.filter(user=request.user).select_related('project').order_by('-created_at')
        
        total_donations = donations.count()
        total_amount = donations.filter(status='completed').aggregate(total=Sum('amount'))['total'] or 0
        completed_donations = donations.filter(status='completed').count()
        
        user_age_group = request.user.age_group
        age_group_settings = AgeGroupSettings.objects.filter(
            age_group=user_age_group, is_active=True
        ).first()
        
        return render(request, 'charity/user_donations.html', {
            'donations': donations,
            'total_donations': total_donations,
            'total_amount': total_amount,
            'completed_donations': completed_donations,
            'user_age_group': user_age_group,
            'age_group_settings': age_group_settings,
        })
    except Exception as e:
        messages.error(request, f'خطا در بارگذاری تاریخچه کمک‌ها: {str(e)}')
        return redirect('charity_home')

@login_required
def charity_volunteer(request, project_id):
    try:
        project = get_object_or_404(CharityProject, id=project_id, is_active=True, status='active')
        
        if CharityVolunteer.objects.filter(user=request.user, project=project).exists():
            messages.info(request, 'شما قبلاً برای این پروژه درخواست داوطلبی داده‌اید')
            return redirect('charity_project_detail', project_id=project_id)
        
        if request.method == 'POST':
            form = CharityVolunteerForm(request.POST)
            if form.is_valid():
                volunteer = form.save(commit=False)
                volunteer.user = request.user
                volunteer.project = project
                volunteer.save()
                messages.success(request, 'درخواست داوطلبی شما با موفقیت ثبت شد. پس از تایید ادمین با شما تماس گرفته خواهد شد.')
                return redirect('charity_project_detail', project_id=project_id)
        else:
            form = CharityVolunteerForm()
        
        user_age_group = request.user.age_group
        age_group_settings = AgeGroupSettings.objects.filter(
            age_group=user_age_group, is_active=True
        ).first()
        
        return render(request, 'charity/volunteer.html', {
            'project': project,
            'form': form,
            'user_age_group': user_age_group,
            'age_group_settings': age_group_settings,
        })
    except Exception as e:
        messages.error(request, f'خطا در ثبت درخواست داوطلبی: {str(e)}')
        return redirect('charity_project_detail', project_id=project_id)

@login_required
def charity_management(request):
    try:
        if not request.user.is_superuser:
            messages.error(request, 'شما دسترسی به این بخش را ندارید')
            return redirect('charity_home')
        
        total_projects = CharityProject.objects.count()
        total_categories = CharityCategory.objects.count()
        total_donations = CharityDonation.objects.count()
        pending_donations = CharityDonation.objects.filter(status='paid').count()
        total_amount = CharityDonation.objects.filter(status='completed').aggregate(
            total=Sum('amount')
        )['total'] or 0
        
        active_projects = CharityProject.objects.filter(status='active')[:5]
        recent_donations = CharityDonation.objects.all().select_related('user', 'project').order_by('-created_at')[:5]
        pending_volunteers = CharityVolunteer.objects.filter(status='pending').count()
        
        return render(request, 'charity/admin/management.html', {
            'total_projects': total_projects,
            'total_categories': total_categories,
            'total_donations': total_donations,
            'pending_donations': pending_donations,
            'total_amount': total_amount,
            'active_projects': active_projects,
            'recent_donations': recent_donations,
            'pending_volunteers': pending_volunteers,
        })
    except Exception as e:
        messages.error(request, f'خطا در بارگذاری مدیریت خیریه: {str(e)}')
        return redirect('charity_home')

@login_required
def charity_project_management(request):
    try:
        if not request.user.is_superuser:
            messages.error(request, 'شما دسترسی به این بخش را ندارید')
            return redirect('charity_home')
        
        if request.method == 'POST':
            form = CharityProjectForm(request.POST, request.FILES)
            if form.is_valid():
                form.save()
                messages.success(request, 'پروژه خیریه با موفقیت اضافه شد')
                return redirect('charity_project_management')
        else:
            form = CharityProjectForm()
        
        projects = CharityProject.objects.all().select_related('category').order_by('-created_at')
        
        return render(request, 'charity/admin/project_management.html', {
            'form': form,
            'projects': projects,
        })
    except Exception as e:
        messages.error(request, f'خطا در مدیریت پروژه‌ها: {str(e)}')
        return redirect('charity_management')

@login_required
def charity_category_management(request):
    try:
        if not request.user.is_superuser:
            messages.error(request, 'شما دسترسی به این بخش را ندارید')
            return redirect('charity_home')
        
        if request.method == 'POST':
            form = CharityCategoryForm(request.POST, request.FILES)
            if form.is_valid():
                form.save()
                messages.success(request, 'دسته‌بندی با موفقیت اضافه شد')
                return redirect('charity_category_management')
        else:
            form = CharityCategoryForm()
        
        categories = CharityCategory.objects.all().order_by('order')
        
        return render(request, 'charity/admin/category_management.html', {
            'form': form,
            'categories': categories,
        })
    except Exception as e:
        messages.error(request, f'خطا در مدیریت دسته‌بندی‌ها: {str(e)}')
        return redirect('charity_management')

@login_required
def charity_donation_management(request):
    try:
        if not request.user.is_superuser:
            messages.error(request, 'شما دسترسی به این بخش را ندارید')
            return redirect('charity_home')
        
        status_filter = request.GET.get('status', 'all')
        donations = CharityDonation.objects.all().select_related('user', 'project').order_by('-created_at')
        
        if status_filter != 'all':
            donations = donations.filter(status=status_filter)
        
        return render(request, 'charity/admin/donation_management.html', {
            'donations': donations,
            'status_filter': status_filter,
        })
    except Exception as e:
        messages.error(request, f'خطا در مدیریت کمک‌ها: {str(e)}')
        return redirect('charity_management')

@login_required
def approve_charity_donation(request, donation_id):
    try:
        if not request.user.is_superuser:
            messages.error(request, 'شما دسترسی به این بخش را ندارید')
            return redirect('charity_donation_management')
        
        donation = get_object_or_404(CharityDonation, id=donation_id)
        
        if donation.status != 'paid':
            messages.error(request, 'فقط کمک‌های پرداخت شده قابل تایید هستند')
            return redirect('charity_donation_management')
        
        donation.status = 'completed'
        donation.save()
        donation.project.update_current_amount()
        
        messages.success(request, f'کمک {donation.donation_number} تایید شد')
        return redirect('charity_donation_management')
    except Exception as e:
        messages.error(request, f'خطا در تایید کمک: {str(e)}')
        return redirect('charity_donation_management')

@login_required
def reject_charity_donation(request, donation_id):
    try:
        if not request.user.is_superuser:
            messages.error(request, 'شما دسترسی به این بخش را ندارید')
            return redirect('charity_donation_management')
        
        donation = get_object_or_404(CharityDonation, id=donation_id)
        
        if request.method == 'POST':
            donation.admin_notes = request.POST.get('admin_notes', '')
            donation.status = 'rejected'
            donation.save()
            messages.success(request, f'کمک {donation.donation_number} رد شد')
        
        return redirect('charity_donation_management')
    except Exception as e:
        messages.error(request, f'خطا در رد کمک: {str(e)}')
        return redirect('charity_donation_management')

@login_required
def charity_update_management(request, project_id):
    try:
        if not request.user.is_superuser:
            messages.error(request, 'شما دسترسی به این بخش را ندارید')
            return redirect('charity_home')
        
        project = get_object_or_404(CharityProject, id=project_id)
        
        if request.method == 'POST':
            form = CharityUpdateForm(request.POST, request.FILES)
            if form.is_valid():
                update = form.save(commit=False)
                update.project = project
                update.created_by = request.user
                update.save()
                messages.success(request, 'به‌روزرسانی با موفقیت اضافه شد')
                return redirect('charity_update_management', project_id=project_id)
        else:
            form = CharityUpdateForm()
        
        updates = project.updates.all().order_by('-created_at')
        
        return render(request, 'charity/admin/update_management.html', {
            'project': project,
            'form': form,
            'updates': updates,
        })
    except Exception as e:
        messages.error(request, f'خطا در مدیریت به‌روزرسانی‌ها: {str(e)}')
        return redirect('charity_management')

@login_required
def charity_volunteer_management(request):
    try:
        if not request.user.is_superuser:
            messages.error(request, 'شما دسترسی به این بخش را ندارید')
            return redirect('charity_home')
        
        status_filter = request.GET.get('status', 'pending')
        volunteers = CharityVolunteer.objects.all().select_related('user', 'project').order_by('-applied_at')
        
        if status_filter != 'all':
            volunteers = volunteers.filter(status=status_filter)
        
        return render(request, 'charity/admin/volunteer_management.html', {
            'volunteers': volunteers,
            'status_filter': status_filter,
        })
    except Exception as e:
        messages.error(request, f'خطا در مدیریت داوطلبان: {str(e)}')
        return redirect('charity_management')

@login_required
def approve_charity_volunteer(request, volunteer_id):
    try:
        if not request.user.is_superuser:
            messages.error(request, 'شما دسترسی به این بخش را ندارید')
            return redirect('charity_volunteer_management')
        
        volunteer = get_object_or_404(CharityVolunteer, id=volunteer_id)
        
        volunteer.status = 'active'
        volunteer.approved_at = timezone.now()
        volunteer.save()
        
        messages.success(request, f'داوطلب {volunteer.user.get_full_name()} تایید شد')
        return redirect('charity_volunteer_management')
    except Exception as e:
        messages.error(request, f'خطا در تایید داوطلب: {str(e)}')
        return redirect('charity_volunteer_management')

@login_required
def reject_charity_volunteer(request, volunteer_id):
    try:
        if not request.user.is_superuser:
            messages.error(request, 'شما دسترسی به این بخش را ندارید')
            return redirect('charity_volunteer_management')
        
        volunteer = get_object_or_404(CharityVolunteer, id=volunteer_id)
        
        if request.method == 'POST':
            volunteer.admin_notes = request.POST.get('admin_notes', '')
            volunteer.status = 'rejected'
            volunteer.save()
            messages.success(request, f'درخواست داوطلبی {volunteer.user.get_full_name()} رد شد')
        
        return redirect('charity_volunteer_management')
    except Exception as e:
        messages.error(request, f'خطا در رد داوطلب: {str(e)}')
        return redirect('charity_volunteer_management')