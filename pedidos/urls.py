from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='inicio'),
    path('nuevo/', views.nuevo_pedido, name='nuevo_pedido'),
    path('pedidos/', views.lista_pedidos, name='lista_pedidos'),
    path('pedidos/marcar_listo/<int:pedido_id>/', views.marcar_listo, name='marcar_listo'),
    path('pedidos/dia/', views.pedidos_del_dia, name='pedidos_del_dia'),
    path('caja/', views.caja_admin, name='caja_admin'),
    path('caja/cerrar/', views.cerrar_caja, name='cerrar_caja'),
    #carga de clientes de pedidos
    path('clientes/carga/', views.carga_clientes, name='carga_clientes'),
    path('productos/carga/', views.carga_productos, name='carga_productos'),
    path('sabores/carga/', views.carga_sabores, name='carga_sabores'),
    path('editar_pedido/<int:pedido_id>/', views.editar_pedido, name='editar_pedido'),
]
