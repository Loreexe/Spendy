from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers

from .models import GlobalSettings, User


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = (
            "id",
            "email",
            "username",
            "status",
            "is_global_admin",
            "date_joined",
        )
        read_only_fields = fields


class RegisterSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True, trim_whitespace=False)
    password_confirm = serializers.CharField(write_only=True, trim_whitespace=False)

    def validate_email(self, value: str) -> str:
        # La verifica dei duplicati resta nella view: la risposta deve essere
        # identica a una registrazione riuscita per non rivelare se l'email è
        # già associata a un account (BUG-007).
        return value.strip().lower()

    def validate(self, attrs):
        if attrs["password"] != attrs["password_confirm"]:
            raise serializers.ValidationError(
                {"password_confirm": "Le password non coincidono."}
            )
        try:
            validate_password(attrs["password"])
        except DjangoValidationError as exc:
            raise serializers.ValidationError({"password": list(exc.messages)}) from exc
        return attrs

    def create(self, validated_data) -> User:
        validated_data.pop("password_confirm")
        password = validated_data.pop("password")
        mode = GlobalSettings.load().registration_mode
        status = (
            User.Status.ACTIVE
            if mode == GlobalSettings.RegistrationMode.OPEN
            else User.Status.PENDING
        )
        user = User(email=validated_data["email"], status=status)
        user.set_password(password)
        user.save()
        return user


class LoginSerializer(serializers.Serializer):
    identifier = serializers.CharField()
    password = serializers.CharField(write_only=True, trim_whitespace=False)


class SetupSerializer(serializers.Serializer):
    password = serializers.CharField(write_only=True, trim_whitespace=False)
    password_confirm = serializers.CharField(write_only=True, trim_whitespace=False)

    def validate(self, attrs):
        if attrs["password"] != attrs["password_confirm"]:
            raise serializers.ValidationError(
                {"password_confirm": "Le password non coincidono."}
            )
        return attrs


class ProfileUpdateSerializer(serializers.Serializer):
    email = serializers.EmailField(required=False, allow_blank=True)

    def validate_email(self, value: str) -> str:
        email = value.strip().lower()
        if not email:
            return email
        queryset = User.objects.filter(email__iexact=email)
        if self.context["request"].user.pk:
            queryset = queryset.exclude(pk=self.context["request"].user.pk)
        if queryset.exists():
            raise serializers.ValidationError("Esiste già un account con questa email.")
        return email


class GlobalSettingsSerializer(serializers.ModelSerializer):
    class Meta:
        model = GlobalSettings
        fields = ("registration_mode", "setup_completed")
        read_only_fields = ("setup_completed",)
