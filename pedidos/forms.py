#para carga de clientes antes del pedido
from .models import Cliente, Sabor, Producto
from .utils import enviar_whatsapp
from django import forms
class ClienteForm(forms.ModelForm):
    class Meta:
        model = Cliente
        fields = ['nombre','apellido','telefono', 'es_mesa']
        widgets = {
            'nombre': forms.TextInput(attrs={'class': 'form-control'}),
            'apellido': forms.TextInput(attrs={'class': 'form-control'}),
            'telefono': forms.TextInput(attrs={'class': 'form-control'}),
            'es_mesa': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }   
        labels = {
            'nombre': 'Nombre',
            'apellido': 'Apellido',
            'telefono': 'Teléfono',
            'es_mesa': 'Es Mesa',
        }   
    help_texts = {
            'telefono': 'Ingrese el número de WhatsApp o teléfono del cliente.',
        }
    def clean_telefono(self):
        telefono = self.cleaned_data.get('telefono')
        if telefono and not telefono.replace("+", "").replace(" ", "").isdigit():
            raise forms.ValidationError("El número de teléfono solo debe contener dígitos, espacios o el símbolo '+'.")
        return telefono
class ProductoForm(forms.ModelForm):
    class Meta:
        model = Producto
        fields = ['nombre', 'precio', 'disponible', 'categoria']
        widgets = {
            'nombre': forms.TextInput(attrs={'class': 'form-control'}),
            'precio': forms.NumberInput(attrs={'class': 'form-control'}),
            'categoria': forms.Select(attrs={'class': 'form-control'}),
            'disponible': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
        labels = {
            'nombre': 'Nombre del Producto',
            'precio': 'Precio (Gs)',
            'categoria': 'Categoría',
            'disponible': 'Disponible',
        }
    help_texts = {
            'precio': 'Ingrese el precio en Guaraníes (Gs).',
        }
class SaborForm(forms.ModelForm):
    class Meta:
        model = Sabor
        fields = ['nombre', 'descripcion']
        widgets = {
            'nombre': forms.TextInput(attrs={'class': 'form-control'}),
            'descripcion': forms.Textarea(attrs={'class': 'form-control'}),
        }
        labels = {
            'nombre': 'Nombre del Sabor',
            'descripcion': 'Descripción del Sabor',
        }
    help_texts = {
            'nombre': 'Ingrese el nombre del sabor de pizza.',
            'descripcion': 'Ingrese una descripción breve del sabor.',
        }

