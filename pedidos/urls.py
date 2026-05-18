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

    # clientes
    path('clientes/carga/', views.carga_clientes, name='carga_clientes'),
    path('clientes/lista/', views.lista_clientes, name='lista_clientes'),
    path('clientes/editar/<int:cliente_id>/', views.editar_cliente, name='editar_cliente'),
    path('clientes/nuevo_ajax/', views.nuevo_cliente_ajax, name='nuevo_cliente_ajax'),

    # productos y sabores
    path('productos/carga/', views.carga_productos, name='carga_productos'),
    path('productos/lista/', views.listar_productos, name='listar_productos'),
    path('productos/editar/<int:producto_id>/', views.editar_producto, name='editar_producto'),
    path('sabores/carga/', views.carga_sabores, name='carga_sabores'),

    # pedidos
    path('editar_pedido/<int:pedido_id>/', views.editar_pedido, name='editar_pedido'),
    path('pedidos/eliminar/<int:pedido_id>/', views.eliminar_pedido, name='eliminar_pedido'),

    # gastos
    path('gastos/carga/', views.registrar_gasto, name='carga_gastos'),

    # reportes
    path('pedidos/balance-mensual/', views.balance_mensual, name='balance_mensual'),
    path('pedidos/balance-diario/', views.balance_diario, name='balance_diario'),
    path('pedidos/ventas-detalladas/', views.ventas_detalladas, name='ventas_detalladas'),

    # caja avanzada
    path('caja/actual/', views.caja_actual_view, name='caja_actual'),
    path('caja/cobrar_credito/', views.cobrar_credito, name='cobrar_credito'),
    path('cobrar_credito_post/', views.cobrar_credito_post, name='cobrar_credito_post'),

    # menú diario
    path('menus-diarios/carga/', views.menu_diario, name='menu_diario'),
]