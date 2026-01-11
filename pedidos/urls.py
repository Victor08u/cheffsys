from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='inicio'),
    path('nuevo/', views.nuevo_pedido, name='nuevo_pedido'),
    path('pedidos/', views.lista_pedidos, name='lista_pedidos'),
    path('pedidos/pendientes/', views.lista_pedidos_pendientes, name='lista_pedidos_pendientes'),
    path('pedidos/marcar_listo/<int:pedido_id>/', views.marcar_listo, name='marcar_listo'),
    path('pedidos/dia/', views.pedidos_del_dia, name='pedidos_del_dia'),
    path('caja/', views.caja_admin, name='caja_admin'),
    path('caja/cerrar/', views.cerrar_caja, name='cerrar_caja'),
    #carga de clientes de pedidos
    path('clientes/carga/', views.carga_clientes, name='carga_clientes'),
    path('productos/carga/', views.carga_productos, name='carga_productos'),
    path('sabores/carga/', views.carga_sabores, name='carga_sabores'),
    path('editar_pedido/<int:pedido_id>/', views.editar_pedido, name='editar_pedido'),
    path('gastos/carga/', views.registrar_gasto, name='carga_gastos'),
    path('pedidos/eliminar/<int:pedido_id>/', views.eliminar_pedido, name='eliminar_pedido'),
    path('clientes/nuevo_ajax/', views.nuevo_cliente_ajax, name='nuevo_cliente_ajax'),
    path('pedidos/balance-mensual/', views.balance_mensual, name='balance_mensual'),
    path('pedidos/balance-diario/', views.balance_diario, name='balance_diario'),
    path('pedidos/ventas-detalladas/', views.ventas_detalladas, name='ventas_detalladas'),
    path('caja/actual/', views.caja_actual_view, name='caja_actual'),


    path('productos/lista/', views.listar_productos, name='listar_productos'),
    path('productos/editar/<int:producto_id>/', views.editar_producto, name='editar_producto'),

]
