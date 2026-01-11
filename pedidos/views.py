from django.forms import ValidationError
from django.shortcuts import get_object_or_404, render, redirect
from .models import Gasto, Sabor, Tamano, Producto, Pedido, DetallePedido, CierreCaja, Cliente
from django.template.loader import render_to_string
from django.http import JsonResponse
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.utils import timezone
import pdfkit
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from .utils import enviar_whatsapp
from django.urls import reverse
import json
from django.db import transaction











def index(request):
    return render(request, 'pedidos/index.html')


from django.shortcuts import render, redirect

@transaction.atomic
def nuevo_pedido(request):
    tamanos = Tamano.objects.all()
    sabores = Sabor.objects.all()
    productos = Producto.objects.filter(disponible=True)
    clientes = Cliente.objects.all()

    if request.method == 'POST':
        tipo_entrega = request.POST.get('tipo_entrega')
        cliente_id = request.POST.get('cliente', '')
        cliente = Cliente.objects.get(id=cliente_id) if cliente_id else None
        observacion_general = request.POST.get('observacion_general', '')
        ind_bancario = request.POST.get('ind_bancario') == '1'

        try:
            pedido = Pedido.objects.create(
                tipo_entrega=tipo_entrega,
                cliente=cliente,
                observacion_general=observacion_general,
                ind_bancario=ind_bancario
            )

            items = int(request.POST.get('total_items', 0))
            productos_agregados = 0  # para controlar si se cargaron productos válidos

            for i in range(1, items + 1):
                tipo_item = request.POST.get(f'tipo_item_{i}')
                if tipo_item == 'pizza':
                    tamano_id = request.POST.get(f'tamano_{i}')
                    if not tamano_id:
                        continue
                    try:
                        tamano = Tamano.objects.get(id=tamano_id)
                    except Tamano.DoesNotExist:
                        continue

                    sabores_ids = request.POST.getlist(f'sabores_{i}')
                    observacion = request.POST.get(f'observacion_{i}', '')
                    con_borde = request.POST.get(f'borde_{i}') == '1'

                    detalle = DetallePedido.objects.create(
                        pedido=pedido,
                        tamano=tamano,
                        con_borde=con_borde,
                        observacion=observacion
                    )
                    detalle.sabores.set(sabores_ids)
                    productos_agregados += 1

                else:
                    producto_id = request.POST.get(f'producto_{i}')
                    if not producto_id:
                        continue

                    try:
                        producto = Producto.objects.get(id=producto_id)
                    except Producto.DoesNotExist:
                        continue  # evita el error y sigue con el siguiente ítem

                    cantidad = int(request.POST.get(f'cantidad_{i}', 1))
                    observacion = request.POST.get(f'observacion_{i}', '')

                    DetallePedido.objects.create(
                        pedido=pedido,
                        producto=producto,
                        cantidad=cantidad,
                        observacion=observacion
                    )
                    productos_agregados += 1

            # Si no se cargó ningún ítem, no guardar pedido
            if productos_agregados == 0:
                pedido.delete()
                return render(request, 'pedidos/nuevo_pedido.html', {
                    'tamanos': tamanos,
                    'sabores': sabores,
                    'productos': productos,
                    'clientes': clientes,
                    'error': 'Debe agregar al menos un producto o pizza válido.'
                })

            pedido.calcular_total()

            return render(request, 'pedidos/nuevo_pedido.html', {
                'tamanos': tamanos,
                'sabores': sabores,
                'productos': productos,
                'clientes': clientes,
                'pedido_guardado': True,
            })

        except Exception as e:
            # rollback automático por @transaction.atomic
            print("Error al crear pedido:", e)
            return render(request, 'pedidos/nuevo_pedido.html', {
                'tamanos': tamanos,
                'sabores': sabores,
                'productos': productos,
                'clientes': clientes,
                'error': 'Error al crear el pedido. Verifique los datos ingresados.'
            })

    return render(request, 'pedidos/nuevo_pedido.html', {
        'tamanos': tamanos,
        'sabores': sabores,
        'productos': productos,
        'clientes': clientes
    })


def editar_pedido(request, pedido_id):
    # Obtener el pedido existente o lanzar 404
    pedido = get_object_or_404(Pedido.objects.prefetch_related('detalles'), id=pedido_id)

    # Datos para el formulario
    tamanos = Tamano.objects.all()
    sabores = Sabor.objects.all()
    productos = Producto.objects.filter(disponible=True)
    clientes = Cliente.objects.all()

    # Evitar edición si el pedido está cerrado
    if pedido.estado == 'cerrado':
        return redirect('pedidos_del_dia')

    if request.method == 'POST':
        tipo_entrega = request.POST.get('tipo_entrega')
        cliente_id = request.POST.get('cliente', '')
        cliente = Cliente.objects.get(id=cliente_id) if cliente_id else None
        observacion_general = request.POST.get('observacion_general', '')
        ind_bancario = request.POST.get('ind_bancario') == '1'

        try:
            with transaction.atomic():
                # --- 1. Actualizar Pedido ---
                pedido.tipo_entrega = tipo_entrega
                pedido.cliente = cliente
                pedido.observacion_general = observacion_general
                pedido.ind_bancario = ind_bancario
                pedido.save(update_fields=['tipo_entrega', 'cliente', 'observacion_general', 'ind_bancario'])

                # --- 2. Procesar ítems ---
                detalles_a_mantener = set()
                total_items = int(request.POST.get('total_items', 0))

                for i in range(1, total_items + 1):
                    detalle_id = request.POST.get(f'detalle_id_{i}')
                    tipo_item = request.POST.get(f'tipo_item_{i}')

                    try:
                        cantidad = int(request.POST.get(f'cantidad_{i}', 1))
                    except ValueError:
                        cantidad = 1

                    detalle = None
                    if detalle_id and detalle_id.isdigit():
                        detalle = DetallePedido.objects.filter(id=int(detalle_id), pedido=pedido).first()

                    if not detalle:
                        detalle = DetallePedido(pedido=pedido)

                    observacion = request.POST.get(f'observacion_{i}', '')

                    if tipo_item == 'pizza':
                        tamano_id = request.POST.get(f'tamano_{i}')
                        sabores_ids = request.POST.getlist(f'sabores_{i}')
                        con_borde = request.POST.get(f'borde_{i}') == '1'

                        tamano = Tamano.objects.get(id=tamano_id) if tamano_id else None

                        detalle.tamano = tamano
                        detalle.producto = None
                        detalle.cantidad = cantidad
                        detalle.con_borde = con_borde
                        detalle.observacion = observacion

                        detalle.full_clean()
                        detalle.save()  # 🔹 Guardar antes de set()
                        detalle.sabores.set(sabores_ids)

                    else:  # Productos normales
                        producto_id = request.POST.get(f'producto_{i}')
                        producto = Producto.objects.get(id=producto_id) if producto_id else None

                        detalle.producto = producto
                        detalle.cantidad = cantidad
                        detalle.tamano = None
                        detalle.con_borde = False
                        detalle.observacion = observacion

                        detalle.full_clean()
                        detalle.save()
                        detalle.sabores.clear()

                    detalles_a_mantener.add(detalle.id)

                # --- 3. Eliminar ítems marcados como eliminados ---
                eliminados_raw = request.POST.get('detalles_eliminados', '')
                ids_eliminados = [int(i) for i in eliminados_raw.split(',') if i.isdigit()]
                if ids_eliminados:
                    DetallePedido.objects.filter(pedido=pedido, id__in=ids_eliminados).delete()

                # --- 4. Eliminar ítems no enviados (por seguridad adicional) ---
                DetallePedido.objects.filter(pedido=pedido).exclude(id__in=list(detalles_a_mantener)).delete()

                # --- ✅ 5. Recalcular total ---
                pedido.refresh_from_db()
                pedido.calcular_total()

                return render(request, 'pedidos/editar_pedido.html', {
                    'tamanos': tamanos,
                    'sabores': sabores,
                    'productos': productos,
                    'clientes': clientes,
                    'pedido': pedido,
                    'pedido_actualizado': True,
                    'detalles_json': get_detalles_json(pedido),
                })

        except ValidationError as e:
            error_message = f"Error de validación: {e.message_dict}"
        except Exception as e:
            error_message = f"Ocurrió un error: {e}"

    # --- GET o POST con error ---
    detalles_json = get_detalles_json(pedido)
    context = {
        'pedido': pedido,
        'tamanos': tamanos,
        'sabores': sabores,
        'productos': productos,
        'clientes': clientes,
        'detalles_json': detalles_json,
    }
    return render(request, 'pedidos/editar_pedido.html', context)


def get_detalles_json(pedido):
    detalles_data = []
    for detalle in pedido.detalles.all():
        data = {
            'id': detalle.id,
            'observacion': detalle.observacion,
        }

        if detalle.tamano:
            data['tipo'] = 'pizza'
            data['tamano_id'] = detalle.tamano.id
            data['con_borde'] = detalle.con_borde
            data['sabores_ids'] = list(detalle.sabores.values_list('id', flat=True))
        elif detalle.producto:
            data['tipo'] = detalle.producto.categoria
            data['producto_id'] = detalle.producto.id
            data['cantidad'] = detalle.cantidad
        else:
            continue

        detalles_data.append(data)

    return json.dumps(detalles_data)

def lista_pedidos(request):
    #ORDENAR POR FECHA ASCENDENTE YA QUE LO QUE INGRESA PRIMERO DEBE APARECER PRIMERO y filtrar por pendientes
    pedidos = Pedido.objects.filter(estado='pendiente').order_by('fecha')
    for pedido in pedidos:
        pedido.tiene_menu = any(
            d.producto and d.producto.categoria == 'menu'
            for d in pedido.detalles.all()
        )
    return render(request, 'pedidos/lista_pedidos.html', {'pedidos': pedidos})

def lista_pedidos_pendientes(request):
    #ORDENAR POR FECHA ASCENDENTE YA QUE LO QUE INGRESA PRIMERO DEBE APARECER PRIMERO y filtrar por pendientes
    pedidos = Pedido.objects.filter(estado='pendiente').order_by('fecha')
    for pedido in pedidos:
        pedido.tiene_menu = any(
            d.producto and d.producto.categoria == 'menu'
            for d in pedido.detalles.all()
        )
    return render(request, 'pedidos/pedidos_pendientes.html', {'pedidos': pedidos})

def marcar_listo(request, pedido_id):
    if request.method == "POST":
        try:
            pedido = (
                Pedido.objects
                .select_related("cliente")
                .prefetch_related("detalles__producto", "detalles__sabores", "detalles__tamano")
                .get(id=pedido_id)
            )

            pedido.estado = "listo"
            pedido.save()

            cliente = pedido.cliente
            enlace_whatsapp = None

            # 🔹 Generar detalle del pedido
            detalles = []
            for d in pedido.detalles.all():
                if d.producto:
                    detalles.append(f"{d.cantidad} x {d.producto.nombre}")
                elif d.tamano:
                    sabores = ", ".join(s.nombre for s in d.sabores.all())
                    detalles.append(f"Pizza {d.tamano.nombre} - {sabores or 'Sin sabores'}")

            detalle_texto = "\n".join(detalles)
            total = f"{int(pedido.total):,}".replace(",", ".")  # ejemplo: 52.000

            # 🔹 Crear mensaje según tipo de entrega
            if pedido.tipo_entrega == "local":
                mensaje = (
                    f"✅ Pedido Nro {pedido.id} listo para servir en el local 🍽️\n\n"
                    f"Detalle:\n{detalle_texto}\n\n"
                    f"Importe Total: {total} Gs"
                )

            elif pedido.tipo_entrega == "delivery" and cliente:
                mensaje = (
                    f"🏍️ ¡Hola {cliente.nombre or ''}! Tu pedido Nro {pedido.id} ya está en camino 🎉\n\n"
                    f"Detalle:\n{detalle_texto}\n\n"
                    f"Importe Total: {total} Gs\n\n"
                    f"Gracias por tu preferencia"
                )
                enlace_whatsapp = enviar_whatsapp(cliente, mensaje)

            elif pedido.tipo_entrega == "retiro" and cliente:
                mensaje = (
                    f"🎉 ¡Hola {cliente.nombre or ''}! Tu pedido Nro {pedido.id} está listo para ser retirado 🍕\n\n"
                    f"Aquí tienes el detalle:\n{detalle_texto}\n\n"
                    f"Importe Total: {total} Gs\n\n"
                    f"Gracias por elegirnos"
                )
                enlace_whatsapp = enviar_whatsapp(cliente, mensaje)

            else:
                mensaje = f"Pedido Nro {pedido.id} actualizado."

            return JsonResponse({
                "success": True,
                "whatsapp": enlace_whatsapp,
                "mensaje": mensaje
            })

        except Pedido.DoesNotExist:
            return JsonResponse({"success": False, "error": "Pedido no encontrado"})

    return JsonResponse({"success": False, "error": "Método no permitido"})

def pedidos_del_dia(request): 
    # Filtrar pedidos por fecha que se recibe por GET 
    fecha_str = request.GET.get('fecha') 
    if fecha_str: 
        fecha = timezone.datetime.strptime(fecha_str, '%Y-%m-%d').date() 
        pedidos = Pedido.objects.filter(fecha__date=fecha).order_by('fecha') 
    else: 
        fecha = timezone.now().date() 
        pedidos = Pedido.objects.filter(fecha__date=fecha).order_by('fecha') 
    total_dia = sum(p.total for p in pedidos) 
    return render(request, 'pedidos/pedidos_del_dia.html', { 
        'hoy': fecha, 
        'pedidos': pedidos, 
        'total_dia': total_dia, 
        })


def caja_admin(request):
    # Pedidos listos que aún no fueron cerrados en forma descendente
    pedidos_listos = Pedido.objects.filter(estado='listo', cierre_caja__isnull=True).order_by('-fecha')
    gastos = Gasto.objects.filter(cerrado=False)
    return render(request, 'pedidos/caja_admin.html', {'pedidos': pedidos_listos, 'gastos': gastos})

@csrf_exempt
def cerrar_caja(request):
    pedidos_listos = list(Pedido.objects.filter(estado='listo', cierre_caja__isnull=True))
    gastos = list(Gasto.objects.filter(cerrado=False))

    if not pedidos_listos and not gastos:
        return HttpResponse("No hay pedidos ni gastos pendientes para cerrar.", status=400)

    # Obtener el saldo anterior desde el último cierre
    ultimo_cierre = CierreCaja.objects.order_by('-fecha_hora').first()
    saldo_anterior = ultimo_cierre.saldo_actual if ultimo_cierre else Decimal('0')

    # Totales de ventas
    total_ventas = sum(p.total or 0 for p in pedidos_listos)
    total_banco = sum(p.total for p in pedidos_listos if getattr(p, 'ind_bancario', False))
    total_efectivo = total_ventas - total_banco

    # Totales de gastos
    total_gastos = sum(g.monto for g in gastos)
    total_gastos_bancarios = sum(g.monto for g in gastos if getattr(g, 'ind_bancario', False))
    total_gastos_efectivo = total_gastos - total_gastos_bancarios

    # 💰 Saldo actual = saldo anterior + todas las ventas (efectivo + transferencias) - gastos
    saldo_actual = saldo_anterior + total_ventas - total_gastos


    # Crear cierre
    cierre = CierreCaja.objects.create(
        saldo_anterior=saldo_anterior,
        total_ventas=total_ventas,
        total_gastos=total_gastos,
        saldo_actual=saldo_actual,
        saldo_efectivo_anterior=ultimo_cierre.saldo_efectivo if ultimo_cierre else 0,
        saldo_bancario_anterior=ultimo_cierre.saldo_bancario if ultimo_cierre else 0,
        saldo_efectivo= (ultimo_cierre.saldo_efectivo if ultimo_cierre else 0) + total_efectivo - total_gastos_efectivo,
        saldo_bancario=(ultimo_cierre.saldo_bancario if ultimo_cierre else 0) + total_banco - total_gastos_bancarios,

    )

    # Asociar pedidos y gastos al cierre
    Pedido.objects.filter(id__in=[p.id for p in pedidos_listos]).update(estado='cerrado', cierre_caja=cierre)
    Gasto.objects.filter(id__in=[g.id for g in gastos]).update(cerrado=True, cierre_caja=cierre)

    # 🧾 Generar PDF
    path_wkhtmltopdf = r"C:\Program Files\wkhtmltopdf\bin\wkhtmltopdf.exe"
    config = pdfkit.configuration(wkhtmltopdf=path_wkhtmltopdf)

    html = render_to_string('pedidos/arqueo_cierre.html', {
        'pedidos': pedidos_listos,
        'gastos': gastos,
        'cierre': cierre,
        'saldo_anterior': saldo_anterior,
        'total_ventas': total_ventas,
        'total_banco': total_banco,
        'total_efectivo': total_efectivo,
        'total_gastos': total_gastos,
        'saldo_actual': saldo_actual,
    })

    pdf = pdfkit.from_string(html, False, configuration=config)
    response = HttpResponse(pdf, content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="arqueo_{cierre.fecha_hora.strftime("%Y%m%d_%H%M")}.pdf"'
    return response

def caja_actual_view(request):
    ultimo_cierre = CierreCaja.objects.order_by('-fecha_hora').first()
    caja_actual = ultimo_cierre.saldo_actual if ultimo_cierre else 0
    saldo_efectivo = ultimo_cierre.saldo_efectivo if ultimo_cierre else 0
    saldo_bancario = ultimo_cierre.saldo_bancario if ultimo_cierre else 0

    contexto = {
        'caja_actual': caja_actual,
        'saldo_efectivo': saldo_efectivo,
        'saldo_bancario': saldo_bancario,
    }

    return render(request, 'pedidos/caja_actual.html', contexto)

#carga de clientes desde un formulario
from .forms import ClienteForm, GastoForm, ProductoForm, SaborForm
def carga_clientes(request):
    if request.method == 'POST':
        form = ClienteForm(request.POST)
        if form.is_valid():
            form.save()
            return render(request, 'pedidos/carga_clientes.html', {
                'form': ClienteForm(),  # se limpia el formulario
                'clientes': Cliente.objects.all().order_by('nombre'),
                'cliente_guardado': True  # bandera para mostrar el modal
            })
    else:
        form = ClienteForm()

    clientes = Cliente.objects.all().order_by('nombre')
    return render(request, 'pedidos/carga_clientes.html', {
        'form': form,
        'clientes': clientes
    })

def carga_productos(request):
    if request.method == 'POST':
        form = ProductoForm(request.POST)
        if form.is_valid():
            form.save()
            return render(request, 'pedidos/carga_productos.html', {
                'form': ProductoForm(),  # se limpia el formulario
                'productos': Producto.objects.all().order_by('nombre'),
                'producto_guardado': True  # bandera para mostrar el modal
            })
    else:
        form = ProductoForm()
    
    productos = Producto.objects.all().order_by('nombre')
    return render(request, 'pedidos/carga_productos.html', {
        'form': form,
        'productos': productos
    })
def carga_sabores(request):
    if request.method == 'POST':
        form = SaborForm(request.POST)
        if form.is_valid():
            form.save()
            return render(request, 'pedidos/carga_sabores.html', {
                'form': SaborForm(),  # se limpia el formulario
                'sabores': Sabor.objects.all().order_by('nombre'),
                'sabores_guardado': True  # bandera para mostrar el modal
            })
    else:
        form = SaborForm()
    
    sabores = Sabor.objects.all().order_by('nombre')
    return render(request, 'pedidos/carga_sabores.html', {
        'form': form,
        'sabores': sabores
    })


def registrar_gasto(request):
    if request.method == 'POST':
        form = GastoForm(request.POST)
        if form.is_valid():
            form.save()
            return render(request, 'pedidos/carga_gastos.html', {
                'form': GastoForm(),  # se limpia el formulario
                'gastos': Gasto.objects.all().order_by('fecha'),
                'gasto_guardado': True  # bandera para mostrar el modal
            })
    else:
        form = GastoForm()
    
    gastos = Gasto.objects.filter(cerrado=False)
    return render(request, 'pedidos/carga_gastos.html', {'form': form, 'gastos': gastos})

@csrf_exempt
def eliminar_pedido(request, pedido_id):
    from .models import Pedido
    if request.method == "POST":
        try:
            pedido = Pedido.objects.get(id=pedido_id)
            pedido.delete()
            return JsonResponse({"success": True})
        except Pedido.DoesNotExist:
            return JsonResponse({"success": False, "error": "El pedido no existe."})
        except Exception as e:
            return JsonResponse({"success": False, "error": str(e)})
    return JsonResponse({"success": False, "error": "Método no permitido."})

def nuevo_cliente_ajax(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            nombre = data.get('nombre')
            apellido = data.get('apellido')
            telefono = data.get('telefono')

            cliente = Cliente.objects.create(
                nombre=nombre,
                apellido=apellido,
                telefono=telefono
            )

            return JsonResponse({
                'success': True,
                'id': cliente.id,
                'nombre': cliente.nombre,
                'apellido': cliente.apellido,
                'telefono': cliente.telefono
            })
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
    return JsonResponse({'success': False, 'error': 'Método no permitido'})
from datetime import date
from django.db.models import Sum, F
def balance_mensual(request):
    hoy = date.today()
    mes = int(request.GET.get('mes', hoy.month))
    año = int(request.GET.get('año', hoy.year))

    # Filtrar pedidos cerrados del mes
    pedidos = Pedido.objects.filter(fecha__month=mes, fecha__year=año, estado='cerrado')
    gastos = Gasto.objects.filter(fecha__month=mes, fecha__year=año)

    total_ventas = pedidos.aggregate(total=Sum('total'))['total'] or 0
    total_bancario = pedidos.filter(ind_bancario=True).aggregate(total=Sum('total'))['total'] or 0
    total_efectivo = total_ventas - total_bancario
    total_gastos = gastos.aggregate(total=Sum('monto'))['total'] or 0

    balance_final = total_ventas - total_gastos

    contexto = {
        'mes': mes,
        'año': año,
        'total_ventas': total_ventas,
        'total_efectivo': total_efectivo,
        'total_bancario': total_bancario,
        'total_gastos': total_gastos,
        'balance_final': balance_final,
        'pedidos': pedidos,
        'gastos': gastos
    }

    return render(request, 'pedidos/balance_mensual.html', contexto)

def balance_diario(request):
    hoy = date.today()

    # Si viene por GET, usar la fecha seleccionada
    fecha_str = request.GET.get('fecha')

    if fecha_str:
        año, mes, dia = map(int, fecha_str.split('-'))
        fecha = date(año, mes, dia)
    else:
        fecha = hoy

    pedidos = Pedido.objects.filter(fecha__date=fecha, estado='cerrado')
    gastos = Gasto.objects.filter(fecha__date=fecha)

    total_ventas = pedidos.aggregate(total=Sum('total'))['total'] or 0
    total_bancario = pedidos.filter(ind_bancario=True).aggregate(total=Sum('total'))['total'] or 0
    total_efectivo = total_ventas - total_bancario
    total_gastos = gastos.aggregate(total=Sum('monto'))['total'] or 0
    total_gastos_bancarios = gastos.filter(ind_bancario=True).aggregate(total=Sum('monto'))['total'] or 0
    total_gastos_efectivo = total_gastos - total_gastos_bancarios

    balance_final = total_ventas - total_gastos

    # 👉 CAJA ACTUAL
    ultimo_cierre = CierreCaja.objects.last()
    caja_actual = ultimo_cierre.saldo_actual if ultimo_cierre else 0
    saldo_efectivo = (ultimo_cierre.saldo_efectivo if ultimo_cierre else 0)
    saldo_bancario = (ultimo_cierre.saldo_bancario if ultimo_cierre else 0)

    contexto = {
        'fecha': fecha,
        'total_ventas': total_ventas,
        'total_efectivo': total_efectivo,
        'total_bancario': total_bancario,
        'total_gastos': total_gastos,
        'balance_final': balance_final,
        'pedidos': pedidos,
        'gastos': gastos,
        'total_gastos_bancarios': total_gastos_bancarios,
        'total_gastos_efectivo': total_gastos_efectivo,
        'caja_actual': caja_actual,
        'saldo_efectivo': saldo_efectivo,
        'saldo_bancario': saldo_bancario,

    }

    return render(request, 'pedidos/balance_diario.html', contexto)


from django.db.models import Sum, F, FloatField, ExpressionWrapper, IntegerField

def ventas_detalladas(request):
    # 🔹 Filtro de mes y año (por defecto: mes actual)
    mes = request.GET.get('mes')
    anio = request.GET.get('anio')

    hoy = date.today()
    mes = int(mes) if mes else hoy.month
    anio = int(anio) if anio else hoy.year

    detalles = DetallePedido.objects.filter(
        pedido__fecha__month=mes,
        pedido__fecha__year=anio
    )

    # 🔹 Pizzas por tamaño
    pizzas_por_tamano = (
        detalles.filter(tamano__isnull=False)
        .annotate(
            borde_valor=ExpressionWrapper(
                F('con_borde') * 10000,
                output_field=IntegerField()
            )
        )
        .values('tamano__id', 'tamano__nombre')
        .annotate(
            cantidad_total=Sum('cantidad'),
            total_ventas=Sum(
                F('cantidad') * (F('tamano__precio') + F('borde_valor')),
                output_field=FloatField()
            )
        )
        .order_by('-cantidad_total')
    )

    # 🔹 Pizzas por sabor
    pizzas_por_sabor = (
        detalles.filter(tamano__isnull=False, sabores__isnull=False)
        .values('sabores__id', 'sabores__nombre')
        .annotate(
            cantidad_total=Sum('cantidad'),
            total_ventas=Sum(
                F('cantidad') * F('tamano__precio'),
                output_field=FloatField()
            )
        )
        .order_by('-cantidad_total')
    )

    # 🔹 Productos por categoría
    productos_por_categoria = (
        detalles.filter(producto__isnull=False)
        .values('producto__id', 'producto__nombre', 'producto__precio', 'producto__categoria')
        .annotate(
            cantidad_total=Sum('cantidad'),
            total_ventas=Sum(
                F('cantidad') * F('producto__precio'),
                output_field=FloatField()
            )
        )
        .order_by('producto__categoria', '-cantidad_total')
    )

    contexto = {
        'pizzas_por_tamano': pizzas_por_tamano,
        'pizzas_por_sabor': pizzas_por_sabor,
        'productos_por_categoria': productos_por_categoria,
        'mes': mes,
        'anio': anio,
    }

    return render(request, 'pedidos/ventas_detalladas.html', contexto)

def editar_producto(request, producto_id):
    producto = get_object_or_404(Producto, id=producto_id)

    if request.method == 'POST':
        form = ProductoForm(request.POST, instance=producto)
        if form.is_valid():
            form.save()
            return render(request, 'pedidos/editar_producto.html', {
                'form': form,
                'producto': producto,
                'guardado': True
            })
    else:
        form = ProductoForm(instance=producto)

    return render(request, 'pedidos/editar_producto.html', {
        'form': form,
        'producto': producto
    })

def listar_productos(request):
    categoria = request.GET.get('categoria')
    if categoria:
        productos = Producto.objects.filter(categoria=categoria).order_by('nombre')
    else:
        productos = Producto.objects.all().order_by('nombre')
    
    return render(request, 'pedidos/listar_productos.html', {
        'productos': productos
    })