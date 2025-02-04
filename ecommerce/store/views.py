from django.shortcuts import render, HttpResponse
from django.views.generic import ListView, View, DetailView
from django.contrib.auth import login
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.db.models import Q

from .models import Product, Order, Category
from .forms import ProductForm, CustomUserCreationForm 
from .shop import Shelf

shelf = Shelf()

def register(request):
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect('product_list')
    else:
        form = CustomUserCreationForm()
    return render(request, 'store/register.html', {'form': form})



class ProductListView(ListView):
    paginate_by = 10
    model = Product
    template_name = 'store/product_list.html'
    context_object_name = 'products'
    
    def get_queryset(self):
        query = self.request.GET.get('q')
        category_id = self.request.GET.get('category')
        order_by = self.request.GET.get('order_by')
        queryset = Product.objects.all()
        
        if query:
            queryset = queryset.filter(
                Q(name__icontains=query) |
                Q(description__icontains=query)
            )
        
        if category_id:
            queryset = queryset.filter(category_id=category_id)
            print('using category',category_id)
            
        if order_by:
            queryset = queryset.order_by(order_by)
            
        else:
            queryset = queryset.order_by('name')
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['categories'] = Category.objects.all()
        return context
    
def upload_product(request):
    if request.method == 'POST':
        form = ProductForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            return redirect('product_list')
    else:
        form = ProductForm()
    return render(request, 'store/upload_product.html', {'form': form})

class OrderListView(LoginRequiredMixin, ListView):
    model = Order
    template_name = 'store/order_list.html'
    context_object_name = 'orders'
    paginate_by = 10  # Adjust as needed

    def get_queryset(self):
        return Order.objects.filter(user=self.request.user).order_by('-created_at')


class ProductDetailView(DetailView):
    model = Product
    template_name = 'store/product_detail.html'
    context_object_name = 'product'



@login_required
def payment_page(request):
    cart = Cart.objects.get(user=request.user)
    payment_api = shelf.payment
    total_amount = cart.get_total_price()

    if request.method == 'POST':
        reference_code = payment_api.pay(total_amount)
        shelf.buy()
        request.session['reference_code'] = reference_code
        return redirect('payment_confirm')

    return render(request, 'store/payment.html', {'total_amount': total_amount})

@login_required
def payment_confirm(request):
    payment_api = shelf.payment
    reference_code = request.session.get('reference_code')

    if not reference_code:
        return redirect('cart_detail')

    payment_successful = payment_api.confirm(reference_code)

    if payment_successful:
        # Handle successful payment (e.g., clear the cart, create an order, etc.)
        Cart.objects.get(user=request.user).items.clear()  # Clear the cart items
        return render(request, 'store/payment_success.html')
    else:
        return render(request, 'store/payment_failure.html')



class OrderDetailView(LoginRequiredMixin, DetailView):
    model = Order
    template_name = 'store/order_detail.html'
    context_object_name = 'order'

    def get_queryset(self):
        return Order.objects.filter(user=self.request.user)



@login_required
def payment_view(request):
    cart, created = Cart.objects.get_or_create(user=request.user)
    cart_items = cart.items.all()
    total_price = sum(item.product.price * item.quantity for item in cart_items)

    if request.method == 'POST':
        payment_amount = total_price
        payment = shelf.payment 
        reference_code = payment.pay(payment_amount)
        
        if shelf.buy(cart):
            return redirect('order_list')
        else:
            return render(request, 'store/payment.html', {'error': 'Payment failed. Please try again.', 'total_price': total_price})

    return render(request, 'store/payment.html', {'total_price': total_price})



