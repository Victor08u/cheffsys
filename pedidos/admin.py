from django.contrib import admin
from .models import Sabor, Tamano, Producto, Pedido, DetallePedido, CierreCaja, Cliente

admin.site.register(Sabor)
admin.site.register(Tamano)
admin.site.register(Producto)
admin.site.register(Pedido)
admin.site.register(Cliente)    
admin.site.register(DetallePedido)
