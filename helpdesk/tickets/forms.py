from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from django.db.models import Q

from .models import Perfil, Ticket, TicketAdjunto, TicketMensaje


User = get_user_model()


class TicketForm(forms.ModelForm):
    class Meta:
        model = Ticket
        fields = ["asunto", "categoria", "prioridad", "descripcion", "vencimiento"]
        widgets = {
            "asunto": forms.TextInput(
                attrs={"placeholder": "Ej: No puedo ingresar al sistema"}
            ),
            "descripcion": forms.Textarea(
                attrs={
                    "rows": 4,
                    "placeholder": "Describe el problema con el mayor detalle posible",
                }
            ),
            "vencimiento": forms.DateTimeInput(
                attrs={"type": "datetime-local"},
                format="%Y-%m-%dT%H:%M",
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["vencimiento"].required = False
        if self.instance and self.instance.vencimiento:
            self.initial["vencimiento"] = self.instance.vencimiento.strftime("%Y-%m-%dT%H:%M")


class TicketGestionForm(forms.ModelForm):
    class Meta:
        model = Ticket
        fields = ["estado", "prioridad", "categoria", "asignado_a", "vencimiento"]
        widgets = {
            "vencimiento": forms.DateTimeInput(
                attrs={"type": "datetime-local"},
                format="%Y-%m-%dT%H:%M",
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["asignado_a"].required = False
        self.fields["vencimiento"].required = False
        self.fields["asignado_a"].queryset = User.objects.filter(
            Q(perfil__rol=Perfil.Rol.SISTEMAS) | Q(is_superuser=True)
        ).distinct()
        self.fields["asignado_a"].label = "Asignado a"
        if self.instance and self.instance.vencimiento:
            self.initial["vencimiento"] = self.instance.vencimiento.strftime("%Y-%m-%dT%H:%M")


class TicketFiltroForm(forms.Form):
    q = forms.CharField(required=False, label="Buscar")
    estado = forms.ChoiceField(
        required=False,
        choices=[("", "Todos")] + list(Ticket.Estado.choices),
    )
    prioridad = forms.ChoiceField(
        required=False,
        choices=[("", "Todas")] + list(Ticket.Prioridad.choices),
    )
    categoria = forms.ChoiceField(
        required=False,
        choices=[("", "Todas")] + list(Ticket.Categoria.choices),
    )
    solo_vencidos = forms.BooleanField(required=False, label="Solo vencidos")
    asignado_a = forms.ModelChoiceField(
        required=False,
        queryset=User.objects.none(),
        label="Tecnico",
    )

    def __init__(self, *args, **kwargs):
        es_sistemas = kwargs.pop("es_sistemas", False)
        super().__init__(*args, **kwargs)
        if es_sistemas:
            self.fields["asignado_a"].queryset = User.objects.filter(
                Q(perfil__rol=Perfil.Rol.SISTEMAS) | Q(is_superuser=True)
            ).distinct()
        else:
            self.fields.pop("asignado_a")


class MensajePublicoForm(forms.ModelForm):
    class Meta:
        model = TicketMensaje
        fields = ["contenido"]
        widgets = {
            "contenido": forms.Textarea(
                attrs={"rows": 3, "placeholder": "Escribe una respuesta visible para el usuario"}
            )
        }


class ComentarioInternoForm(forms.ModelForm):
    class Meta:
        model = TicketMensaje
        fields = ["contenido"]
        widgets = {
            "contenido": forms.Textarea(
                attrs={"rows": 3, "placeholder": "Comentario interno solo para sistemas"}
            )
        }


class AdjuntoForm(forms.ModelForm):
    class Meta:
        model = TicketAdjunto
        fields = ["archivo"]


class RegistroUsuarioForm(UserCreationForm):
    first_name = forms.CharField(max_length=150, label="Nombre")
    last_name = forms.CharField(max_length=150, label="Apellido")
    email = forms.EmailField(label="Correo electronico")

    class Meta:
        model = User
        fields = ["username", "first_name", "last_name", "email", "password1", "password2"]

    def save(self, commit=True):
        user = super().save(commit=False)
        user.first_name = self.cleaned_data["first_name"]
        user.last_name = self.cleaned_data["last_name"]
        user.email = self.cleaned_data["email"]
        if commit:
            user.save()
            user.perfil.rol = Perfil.Rol.USUARIO
            user.perfil.save(update_fields=["rol"])
        return user


class LoginForm(AuthenticationForm):
    username = forms.CharField(label="Usuario")
    password = forms.CharField(label="Contrasena", widget=forms.PasswordInput)
