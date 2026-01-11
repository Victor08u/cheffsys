from django.db import models
from django.core.exceptions import ValidationError
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver

class Sabor(models.Model):
    nombre = models.CharField(max_length=100)
    descripcion = models.TextField(blank=True, null=True)

    def __str__(self):
        return self.nombre


class Tamano(models.Model):
    nombre = models.CharField(max_length=50)
    porciones = models.IntegerField()
    max_sabores = models.IntegerField()
    precio = models.DecimalField(max_digits=10, decimal_places=2)

    def __str__(self):
        return f"{self.nombre} ({self.porciones} porciones - {self.precio} Gs)"


class Producto(models.Model):
    CATEGORIAS = [
        ('pizza', 'Pizza'),
        ('hamburguesa', 'Hamburguesa'),
        ('papas', 'Papas'),
        ('bebida', 'Bebida'),
        ('menu', 'Menú'),
        ('otro', 'Otro'),
    ]

    nombre = models.CharField(max_length=100)
    categoria = models.CharField(max_length=20, choices=CATEGORIAS)
    precio = models.DecimalField(max_digits=10, decimal_places=2)
    disponible = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.nombre} ({self.categoria})"
class CierreCaja(models.Model):
    fecha_hora = models.DateTimeField(auto_now_add=True)
    saldo_anterior = models.DecimalField(max_digits=12, decimal_places=0, default=0)
    saldo_efectivo_anterior = models.DecimalField(max_digits=12, decimal_places=0, default=0)
    saldo_bancario_anterior = models.DecimalField(max_digits=12, decimal_places=0, default=0)
    # NUEVOS CAMPOS
    saldo_efectivo = models.DecimalField(max_digits=12, decimal_places=0, default=0)
    saldo_bancario = models.DecimalField(max_digits=12, decimal_places=0, default=0)
    total_ventas = models.DecimalField(max_digits=12, decimal_places=0, default=0)
    total_gastos = models.DecimalField(max_digits=12, decimal_places=0, default=0)
    saldo_actual = models.DecimalField(max_digits=12, decimal_places=0, default=0)

    def __str__(self):
        return f"Cierre {self.id} - {self.fecha_hora.strftime('%d/%m/%Y %H:%M')}"
class Cliente(models.Model):
    nombre = models.CharField(max_length=100, blank=True, null=True)
    apellido = models.CharField(max_length=100, blank=True, null=True)
    telefono = models.CharField(max_length=20, blank=True, null=True)  # WhatsApp / teléfono
    es_mesa = models.BooleanField(default=False)  # Indica si es un cliente de mesa sin teléfono

    def __str__(self):
        if self.es_mesa:
            return f"Mesa {self.nombre or 'Sin asignar'}"
        return f"{self.nombre} {self.apellido}"


class Pedido(models.Model):
    fecha = models.DateTimeField(auto_now_add=True)
    cliente = models.ForeignKey(Cliente, on_delete=models.SET_NULL, blank=True, null=True)
    estado = models.CharField(
        max_length=20,
        choices=[('pendiente', 'Pendiente'), ('listo', 'Listo'), ('cerrado', 'Cerrado')],
        default='pendiente'
    )
    tipo_entrega = models.CharField(
        max_length=20,
        choices=[('local', 'En el local'), ('delivery', 'Delivery'), ('retiro', 'Retiro')], default='local'
    )
    total = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    observacion_general = models.TextField(blank=True, null=True)
    ind_bancario = models.BooleanField(default=False)
    cierre_caja = models.ForeignKey(CierreCaja, on_delete=models.SET_NULL, blank=True, null=True)

    def __str__(self):
        return f"Pedido #{self.id} - {self.fecha.strftime('%d/%m/%Y %H:%M')}"

    # 💰 Método para recalcular el total
    def calcular_total(self):
        total = sum(detalle.calcular_subtotal() for detalle in self.detalles.all())
        self.total = total
        self.save(update_fields=['total'])
        return total
    def total_banco(self):
        if self.ind_bancario:
            return self.total
        return 0


class DetallePedido(models.Model):
    pedido = models.ForeignKey(Pedido, on_delete=models.CASCADE, related_name='detalles')

    # --- Pizza ---
    tamano = models.ForeignKey(Tamano, on_delete=models.CASCADE, blank=True, null=True)
    sabores = models.ManyToManyField(Sabor, blank=True)
    con_borde = models.BooleanField(default=False)

    # --- Producto general ---
    producto = models.ForeignKey(Producto, on_delete=models.CASCADE, blank=True, null=True)
    cantidad = models.PositiveIntegerField(default=1)

    observacion = models.TextField(blank=True, null=True)

    def __str__(self):
        if self.producto:
            return f"{self.producto.nombre} x{self.cantidad}"
        elif self.tamano:
            return f"Pizza {self.tamano.nombre}"
        else:
            return "Detalle sin producto"

    def clean(self):
        # Validar que tenga al menos producto o tamaño
        if not self.producto and not self.tamano:
            raise ValidationError("El detalle debe tener al menos un producto o un tamaño de pizza.")

        # ⚠️ Solo validar la cantidad de sabores si el objeto ya está guardado
        if self.pk and self.tamano:
            cant_sabores = self.sabores.count()
            if cant_sabores > self.tamano.max_sabores:
                raise ValidationError(
                    f"El tamaño {self.tamano.nombre} permite un máximo de {self.tamano.max_sabores} sabores."
                )

    # 💰 Subtotal del detalle
    def calcular_subtotal(self):
        if self.producto:
            return self.producto.precio * self.cantidad
        elif self.tamano:
            subtotal = self.tamano.precio
            if self.con_borde:
                subtotal += 10000
            return subtotal
        return 0

def enviar_whatsapp(cliente, mensaje):
    """
    Genera un enlace de WhatsApp Web para enviar mensaje.
    Solo se activa si el cliente tiene teléfono.
    """
    if cliente.telefono:
        numero = cliente.telefono.replace("+", "").replace(" ", "")
        enlace = f"https://wa.me/{numero}?text={mensaje}"
        return enlace
    return None

# 🔁 Señales: recalcula el total al guardar o eliminar detalles
#@receiver([post_save, post_delete], sender=DetallePedido)
#def actualizar_total_pedido(sender, instance, **kwargs):
 #   instance.pedido.calcular_total()


class Gasto(models.Model):
    descripcion = models.CharField(max_length=200)
    monto = models.DecimalField(max_digits=10, decimal_places=2)
    fecha = models.DateTimeField(auto_now_add=True) 
    cerrado = models.BooleanField(default=False)
    cierre_caja = models.ForeignKey('CierreCaja', on_delete=models.SET_NULL, null=True, blank=True)
    ind_bancario = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.descripcion} - Gs. {self.monto:,.0f}"