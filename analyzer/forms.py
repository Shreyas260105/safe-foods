from django import forms
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from django.contrib.auth.models import User

from .models import AnalysisRecord, Product, UserWellnessProfile


class FoodAnalysisForm(forms.Form):
    product = forms.ModelChoiceField(
        queryset=Product.objects.none(),
        required=False,
        empty_label='Choose a predefined product',
        widget=forms.Select(attrs={'class': 'form-select', 'id': 'product-select'})
    )
    ingredient_image = forms.ImageField(
        required=False,
        widget=forms.ClearableFileInput(attrs={'class': 'form-control'})
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['product'].queryset = Product.objects.all()

    def clean(self):
        cleaned_data = super().clean()
        if not cleaned_data.get('product') and not cleaned_data.get('ingredient_image'):
            raise forms.ValidationError('Please choose a product or upload an ingredient label image.')
        return cleaned_data


class RegistrationForm(UserCreationForm):
    first_name = forms.CharField(max_length=150, required=True, widget=forms.TextInput(attrs={'class': 'form-control'}))
    email = forms.EmailField(required=True, widget=forms.EmailInput(attrs={'class': 'form-control'}))

    class Meta:
        model = User
        fields = ('first_name', 'username', 'email', 'password1', 'password2')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name, field in self.fields.items():
            if not field.widget.attrs.get('class'):
                field.widget.attrs['class'] = 'form-control'


class LoginForm(AuthenticationForm):
    username = forms.CharField(widget=forms.TextInput(attrs={'class': 'form-control'}))
    password = forms.CharField(widget=forms.PasswordInput(attrs={'class': 'form-control'}))


class SelfGrowthForm(forms.ModelForm):
    class Meta:
        model = UserWellnessProfile
        fields = ('weight_kg', 'height_cm', 'diet_preference')
        widgets = {
            'weight_kg': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Example: 68'}),
            'height_cm': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Example: 170'}),
            'diet_preference': forms.Select(attrs={'class': 'form-select'}, choices=AnalysisRecord.DIET_CHOICES),
        }

    def clean_weight_kg(self):
        value = self.cleaned_data['weight_kg']
        if value and (value < 20 or value > 250):
            raise forms.ValidationError('Please enter a weight between 20 and 250 kg.')
        return value

    def clean_height_cm(self):
        value = self.cleaned_data['height_cm']
        if value and (value < 100 or value > 250):
            raise forms.ValidationError('Please enter a height between 100 and 250 cm.')
        return value
