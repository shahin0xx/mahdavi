from django.urls import path
from django.conf import settings
from django.conf.urls.static import static
from . import views

urlpatterns = [
    path('test-register/', views.test_register_simple, name='test_register'),
    path('verify-email/', views.verify_email, name='verify_email'),
    path('resend-verification/', views.resend_verification_code, name='resend_verification_code'),
    path('forgot-password/', views.forgot_password, name='forgot_password'),
    path('reset-password/', views.reset_password, name='reset_password'),
    path('change-password/', views.change_password, name='change_password'),
    
    path('', views.home, name='home'),
    path('index/', views.index, name='index'),
    path('login/', views.user_login, name='login'),
    path('register/', views.user_register, name='register'),
    path('logout/', views.user_logout, name='logout'),
    path('profile/', views.profile, name='profile'),
    path('dashboard/', views.dashboard, name='dashboard'),
    
    path('quran/', views.quran, name='quran'),
    path('zecr/', views.zecr, name='zecr'),
    path('time/', views.time, name='time'),
    path('map/', views.map, name='map'),
    
    path('station/<int:station_id>/', views.station_detail, name='station_detail'),
    path('station/<int:station_id>/complete/<str:content_type>/', views.complete_content, name='complete_content'),
    path('station/<int:station_id>/quiz/', views.submit_quiz, name='submit_quiz'),
    
    path('user-achievements/', views.user_achievements, name='user_achievements'),
    path('user-statistics/', views.user_statistics, name='user_statistics'),
    path('user-daily-stats/', views.user_daily_stats, name='user_daily_stats'),
    path('leaderboard/', views.station_leaderboard, name='station_leaderboard'),
    path('api/user-progress/', views.api_user_progress, name='api_user_progress'),
    
    path('admin-dashboard/', views.admin_dashboard, name='admin_dashboard'),
    
    path('games/', views.games_list, name='games_list'),
    path('games/play/<int:game_id>/', views.play_game, name='play_game'),
    path('games/complete/<int:game_id>/', views.complete_game, name='complete_game'),
    path('games/management/', views.game_management, name='game_management'),
    path('games/delete/<int:game_id>/', views.delete_game, name='delete_game'),
    
    path('chat/', views.chat_home, name='chat_home'),
    path('chat/room/<int:room_id>/', views.chat_room, name='chat_room'),
    path('chat/create/', views.create_chat_room, name='create_chat_room'),
    path('chat/private/<int:user_id>/', views.create_private_chat, name='create_private_chat'),
    path('chat/manage/<int:room_id>/', views.manage_chat_room, name='manage_chat_room'),
    path('chat/leave/<int:room_id>/', views.leave_chat_room, name='leave_chat_room'),
    path('chat/search/', views.search_users, name='search_users'),
    path('chat/api/messages/<int:room_id>/', views.api_chat_messages, name='api_chat_messages'),
    path('chat/api/send/<int:room_id>/', views.api_send_message, name='api_send_message'),
    
    path('api/active-audio/', views.ActiveAudioView.as_view(), name='active_audio'),
    
    path('shop/', views.shop_home, name='shop_home'),
    path('shop/products/', views.product_list, name='product_list'),
    path('shop/product/<int:product_id>/', views.product_detail, name='product_detail'),
    path('shop/wishlist/', views.wishlist_view, name='wishlist'),
    path('shop/wishlist/add/<int:product_id>/', views.add_to_wishlist, name='add_to_wishlist'),
    path('shop/wishlist/remove/<int:product_id>/', views.remove_from_wishlist, name='remove_from_wishlist'),
    path('shop/review/<int:product_id>/', views.submit_review, name='submit_review'),
    path('shop/cart/', views.cart_view, name='cart_view'),
    path('shop/cart/add/<int:product_id>/', views.add_to_cart, name='add_to_cart'),
    path('shop/cart/update/<int:cart_item_id>/', views.update_cart, name='update_cart'),
    path('shop/cart/clear/', views.clear_cart, name='clear_cart'),
    path('shop/checkout/', views.checkout, name='checkout'),
    path('shop/payment/<int:order_id>/', views.payment_page, name='payment_page'),
    path('shop/orders/', views.order_list, name='order_list'),
    path('shop/orders/<int:order_id>/', views.order_detail, name='order_detail'),
    path('shop/api/cart-count/', views.api_cart_count, name='api_cart_count'),
    path('shop/api/product-search/', views.api_product_search, name='api_product_search'),
    path('shop/management/', views.shop_management, name='shop_management'),
    path('shop/management/products/', views.product_management, name='product_management'),
    path('shop/management/categories/', views.category_management, name='category_management'),
    path('shop/management/products/delete/<int:product_id>/', views.delete_product, name='delete_product'),
    path('shop/management/categories/delete/<int:category_id>/', views.delete_category, name='delete_category'),
    
    path('social/', views.social_home, name='social_home'),
    path('social/profile/', views.social_profile, name='social_profile'),
    path('social/profile/<int:user_id>/', views.social_profile, name='social_profile'),
    path('social/profile/edit/', views.edit_social_profile, name='edit_social_profile'),
    path('social/post/create/', views.create_post, name='create_post'),
    path('social/post/<int:post_id>/', views.post_detail, name='post_detail'),
    path('social/story/create/', views.create_story, name='create_story'),
    path('social/story/<int:story_id>/', views.story_view, name='story_view'),
    path('social/follow/<int:user_id>/', views.follow_user, name='follow_user'),
    path('social/unfollow/<int:user_id>/', views.unfollow_user, name='unfollow_user'),
    path('social/like/<int:post_id>/', views.like_post, name='like_post'),
    path('social/comment/<int:post_id>/', views.add_comment, name='add_comment'),
    path('social/requests/', views.follow_requests, name='follow_requests'),
    path('social/profile/remove-image/', views.remove_profile_image, name='remove_profile_image'),
    path('social/request/<int:request_id>/<str:action>/', views.handle_follow_request, name='handle_follow_request'),
    
    path('library/', views.library_home, name='library_home'),
    path('library/books/', views.book_list, name='book_list'),
    path('library/book/<int:book_id>/', views.book_detail, name='book_detail'),
    path('library/book/<int:book_id>/add-to-cart/', views.add_book_to_cart, name='add_book_to_cart'),
    path('library/cart/', views.book_cart, name='book_cart'),
    path('library/cart/remove/<int:order_id>/', views.remove_book_from_cart, name='remove_book_from_cart'),
    path('library/checkout/', views.book_checkout, name='book_checkout'),
    path('library/orders/', views.book_orders, name='book_orders'),
    path('library/reader/<int:book_id>/', views.book_reader, name='book_reader'),
    path('library/download/<int:book_id>/', views.download_book, name='download_book'),
    path('library/management/', views.library_management, name='library_management'),
    path('library/management/books/', views.book_management, name='book_management'),
    path('library/management/categories/', views.book_category_management, name='book_category_management'),
    path('library/management/orders/', views.book_order_management, name='book_order_management'),
    path('library/management/orders/approve/<int:order_id>/', views.approve_book_order, name='approve_book_order'),
    path('library/management/orders/reject/<int:order_id>/', views.reject_book_order, name='reject_book_order'),

    path('virtual-tours/', views.virtual_tours_home, name='virtual_tours_home'),
    path('virtual-tours/tour/<int:tour_id>/', views.virtual_tour_view, name='virtual_tour_view'),
    path('virtual-tours/management/', views.virtual_tour_management, name='virtual_tour_management'),
    path('virtual-tours/management/categories/', views.virtual_tour_category_management, name='virtual_tour_category_management'),
    path('virtual-tours/management/delete/<int:tour_id>/', views.delete_virtual_tour, name='delete_virtual_tour'),
    path('virtual-tours/management/categories/delete/<int:category_id>/', views.delete_virtual_tour_category, name='delete_virtual_tour_category'),
   
    path('charity/', views.charity_home, name='charity_home'),
    path('charity/projects/', views.charity_projects, name='charity_projects'),
    path('charity/project/<int:project_id>/', views.charity_project_detail, name='charity_project_detail'),
    path('charity/donate/<int:project_id>/', views.make_donation, name='make_donation'),
    path('charity/payment/<int:donation_id>/', views.charity_payment, name='charity_payment'),
    path('charity/my-donations/', views.charity_donations, name='charity_donations'),
    path('charity/volunteer/<int:project_id>/', views.charity_volunteer, name='charity_volunteer'),

    path('charity/management/', views.charity_management, name='charity_management'),
    path('charity/management/projects/', views.charity_project_management, name='charity_project_management'),
    path('charity/management/categories/', views.charity_category_management, name='charity_category_management'),
    path('charity/management/donations/', views.charity_donation_management, name='charity_donation_management'),
    path('charity/management/donations/approve/<int:donation_id>/', views.approve_charity_donation, name='approve_charity_donation'),
    path('charity/management/donations/reject/<int:donation_id>/', views.reject_charity_donation, name='reject_charity_donation'),
    path('charity/management/updates/<int:project_id>/', views.charity_update_management, name='charity_update_management'),
    path('charity/management/volunteers/', views.charity_volunteer_management, name='charity_volunteer_management'),
    path('charity/management/volunteers/approve/<int:volunteer_id>/', views.approve_charity_volunteer, name='approve_charity_volunteer'),
    path('charity/management/volunteers/reject/<int:volunteer_id>/', views.reject_charity_volunteer, name='reject_charity_volunteer'),
]

handler404 = views.handler404
handler500 = views.handler500
handler403 = views.handler403
handler400 = views.handler400

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)