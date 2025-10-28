from django.forms import ValidationError
from django.shortcuts import get_object_or_404, render, redirect
from .models import Sabor, Tamano, Producto, Pedido, DetallePedido, CierreCaja, Cliente
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

        pedido = Pedido.objects.create(
            tipo_entrega=tipo_entrega,
            cliente=cliente,
            observacion_general=observacion_general,
            ind_bancario=ind_bancario
        )

        items = int(request.POST.get('total_items', 0))
        for i in range(1, items + 1):
            tipo_item = request.POST.get(f'tipo_item_{i}')
            if tipo_item == 'pizza':
                tamano_id = request.POST.get(f'tamano_{i}')
                sabores_ids = request.POST.getlist(f'sabores_{i}')
                observacion = request.POST.get(f'observacion_{i}', '')
                con_borde = request.POST.get(f'borde_{i}') == '1'
                tamano = Tamano.objects.get(id=tamano_id)

                detalle = DetallePedido.objects.create(
                    pedido=pedido,
                    tamano=tamano,
                    con_borde=con_borde,
                    observacion=observacion
                )
                detalle.sabores.set(sabores_ids)
            else:
                producto_id = request.POST.get(f'producto_{i}')
                cantidad = int(request.POST.get(f'cantidad_{i}', 1))
                observacion = request.POST.get(f'observacion_{i}', '')
                producto = Producto.objects.get(id=producto_id)

                DetallePedido.objects.create(
                    pedido=pedido,
                    producto=producto,
                    cantidad=cantidad,
                    observacion=observacion
                )

        pedido.calcular_total()

        # En lugar de redirect directo, renderizamos con flag
        return render(request, 'pedidos/nuevo_pedido.html', {
            'tamanos': tamanos,
            'sabores': sabores,
            'productos': productos,
            'clientes': clientes,
            'pedido_guardado': True,  # bandera para mostrar modal
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
        return redirect('url_a_detalle_pedido', pedido_id=pedido.id)

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

                # --- 3. Eliminar ítems no enviados ---
                DetallePedido.objects.filter(pedido=pedido).exclude(id__in=list(detalles_a_mantener)).delete()

                # --- 4. Recalcular total ---
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
    return render(request, 'pedidos/lista_pedidos.html', {'pedidos': pedidos})


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
    # Pedidos listos que aún no fueron cerrados
    pedidos_listos = Pedido.objects.filter(estado='listo', cierre_caja__isnull=True).order_by('fecha')
    return render(request, 'pedidos/caja_admin.html', {'pedidos': pedidos_listos})

@csrf_exempt
def cerrar_caja(request):
    # Tomar los pedidos listos sin cierre
    pedidos_listos = list(Pedido.objects.filter(estado='listo', cierre_caja__isnull=True))
    
    if not pedidos_listos:
        return HttpResponse("No hay pedidos listos para cerrar.", status=400)
    
    # Crear nuevo cierre
    cierre = CierreCaja.objects.create()
    
    # Calcular total
    total = sum(p.total or 0 for p in pedidos_listos)
    total_banco = sum(p.total for p in pedidos_listos if p.ind_bancario)
    total_efectivo = total - total_banco


    cierre.total_ventas = total
    cierre.save()
    
    # Asociar pedidos al cierre y marcarlos como cerrados
    Pedido.objects.filter(id__in=[p.id for p in pedidos_listos]).update(estado='cerrado', cierre_caja=cierre)
    
    # Generar PDF
    path_wkhtmltopdf = r"C:\Program Files\wkhtmltopdf\bin\wkhtmltopdf.exe"
    config = pdfkit.configuration(wkhtmltopdf=path_wkhtmltopdf)
    html = render_to_string('pedidos/arqueo_cierre.html', {
        'pedidos': pedidos_listos,
        'total': total,
        'cierre': cierre,
        'total_banco': total_banco,
        'total_efectivo': total_efectivo,
    })
    pdf = pdfkit.from_string(html, False, configuration=config)

    response = HttpResponse(pdf, content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="arqueo_{cierre.fecha_hora.strftime("%Y%m%d_%H%M")}.pdf"'
    return response

#carga de clientes desde un formulario
from .forms import ClienteForm, ProductoForm, SaborForm
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


