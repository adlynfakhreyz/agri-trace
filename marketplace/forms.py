from django import forms

from authentication.models import Buyer, Merchant, Seller
from marketplace.models import Product, ProductImage
from django.utils.text import slugify

class MerchantForm(forms.ModelForm):
    class Meta:
        model = Merchant
        fields = ('profile_image',)


class BuyerForm(forms.ModelForm):
    class Meta:
        model = Buyer
        fields = ('location', 'default_shipping_address', 'phone_number')


class SellerRegistrationForm(forms.ModelForm):
    class Meta:
        model = Seller
        fields = ('shop_name', 'shop_description', 'shop_logo', 'shop_banner')


from django import forms
from .models import Category, Product, ProductImage
from django.forms import inlineformset_factory

class ProductForm(forms.ModelForm):
    class Meta:
        model = Product
        fields = ['category', 'name', 'slug', 'description', 'price', 'stock', 'is_featured', 'is_active']
        widgets = {
            'description': forms.Textarea(attrs={'rows': 4}),
            'slug': forms.HiddenInput(),  # Make it hidden in the form
        }

    def __init__(self, *args, seller=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.seller = seller
        # Only include categories with no children (leaf nodes)
        self.fields['category'].queryset = Category.objects.filter(children__isnull=True)
        self.fields['slug'].required = False  # Make it not required


    def save(self, commit=True):
        product = super().save(commit=False)
        if self.seller:
            product.seller = self.seller
        if not product.slug:  # Auto-generate slug if empty
            product.slug = slugify(product.name)
        if commit:
            product.save()
        return product

class ProductImageForm(forms.ModelForm):
    class Meta:
        model = ProductImage
        fields = ['image', 'is_primary']

ProductImageFormSet = inlineformset_factory(
    Product, 
    ProductImage, 
    form=ProductImageForm, 
    extra=3, 
    can_delete=True
)




class CartAddProductForm(forms.Form):
    quantity = forms.IntegerField(min_value=1, initial=1, widget=forms.NumberInput(attrs={'class': 'form-control'}))
    update = forms.BooleanField(required=False, initial=False, widget=forms.HiddenInput)


class ShippingAddressForm(forms.Form):
    shipping_address = forms.CharField(
        widget=forms.Textarea(attrs={'rows': 3}),
        required=True,
        label='Shipping Address'
    )
    billing_address = forms.CharField(
        widget=forms.Textarea(attrs={'rows': 3}),
        required=True,
        label='Billing Address'
    )
    same_as_shipping = forms.BooleanField(
        required=False,
        initial=True,
        label='Same as shipping address',
        widget=forms.CheckboxInput(attrs={'onchange': 'copyShippingAddress(this)'})
    )
    save_default = forms.BooleanField(
        required=False,
        initial=False,
        label='Save as default shipping address'
    )
    
    def clean(self):
        cleaned_data = super().clean()
        same_as_shipping = cleaned_data.get('same_as_shipping')
        shipping_address = cleaned_data.get('shipping_address')
        billing_address = cleaned_data.get('billing_address')
        
        if same_as_shipping and shipping_address:
            cleaned_data['billing_address'] = shipping_address
        
        return cleaned_data


class PaymentForm(forms.Form):
    PAYMENT_CHOICES = (
        ('credit_card', 'Credit Card'),
        ('paypal', 'PayPal'),
    )
    
    payment_method = forms.ChoiceField(
        choices=PAYMENT_CHOICES,
        widget=forms.RadioSelect,
        required=True
    )
    
    # For credit card - in a real app, you would use a more secure approach
    card_number = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={'placeholder': 'Card number'})
    )
    card_expiry = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={'placeholder': 'MM/YY'})
    )
    card_cvv = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={'placeholder': 'CVV'})
    )
    card_holder = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={'placeholder': 'Card holder name'})
    )
    
    def clean(self):
        cleaned_data = super().clean()
        payment_method = cleaned_data.get('payment_method')
        
        if payment_method == 'credit_card':
            card_number = cleaned_data.get('card_number')
            card_expiry = cleaned_data.get('card_expiry')
            card_cvv = cleaned_data.get('card_cvv')
            card_holder = cleaned_data.get('card_holder')
            
            if not all([card_number, card_expiry, card_cvv, card_holder]):
                raise ValidationError('All credit card details are required')
        
        return cleaned_data


class ProductSearchForm(forms.Form):
    query = forms.CharField(required=False, label='Search')
    category = forms.IntegerField(required=False, widget=forms.HiddenInput)
    min_price = forms.DecimalField(required=False, min_value=0)
    max_price = forms.DecimalField(required=False, min_value=0)
    sort_by = forms.ChoiceField(
        required=False,
        choices=(
            ('price_asc', 'Price: Low to High'),
            ('price_desc', 'Price: High to Low'),
            ('newest', 'Newest First'),
            ('rating', 'Best Rating'),
        )
    )