from rest_framework import viewsets, status, generics
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import authenticate
from django.contrib.auth.models import User
import logging

from .models import Patient, Doctor, PatientDoctorMapping
from .serializers import (
    UserRegistrationSerializer,
    UserLoginSerializer,
    PatientSerializer,
    DoctorSerializer,
    PatientDoctorMappingSerializer
)

logger = logging.getLogger('core')


class UserRegistrationView(generics.CreateAPIView):
    queryset = User.objects.all()
    permission_classes = (AllowAny,)
    serializer_class = UserRegistrationSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        logger.info("User registered: %s (%s)", user.email, user.first_name)
        
        return Response({
            "message": "User registered successfully",
            "user": {
                "email": user.email,
                "name": user.first_name
            }
        }, status=status.HTTP_201_CREATED)


class UserLoginView(generics.GenericAPIView):
    permission_classes = (AllowAny,)
    serializer_class = UserLoginSerializer

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        email = serializer.validated_data['email']
        password = serializer.validated_data['password']
        
        user = authenticate(username=email, password=password)
        
        if user is not None:
            logger.info("Login successful: %s", email)
            refresh = RefreshToken.for_user(user)
            return Response({
                "message": "Login successful",
                "tokens": {
                    "refresh": str(refresh),
                    "access": str(refresh.access_token),
                },
                "user": {
                    "email": user.email,
                    "name": user.first_name
                }
            })
        else:
            logger.warning("Login failed for: %s", email)
            return Response({
                "error": "Invalid credentials"
            }, status=status.HTTP_401_UNAUTHORIZED)


class PatientViewSet(viewsets.ModelViewSet):
    serializer_class = PatientSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Patient.objects.filter(created_by=self.request.user)

    def perform_create(self, serializer):
        patient = serializer.save(created_by=self.request.user)
        logger.info("Patient created: %s (ID %s) by user %s", patient, patient.id, self.request.user)

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        if instance.created_by != request.user:
            return Response(
                {"error": "You can only delete your own patients."},
                status=status.HTTP_403_FORBIDDEN
            )
        return super().destroy(request, *args, **kwargs)


class DoctorViewSet(viewsets.ModelViewSet):
    queryset = Doctor.objects.all()
    serializer_class = DoctorSerializer
    permission_classes = [IsAuthenticated]


class PatientDoctorMappingViewSet(viewsets.ModelViewSet):
    serializer_class = PatientDoctorMappingSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return PatientDoctorMapping.objects.filter(patient__created_by=self.request.user)

    @action(detail=False, methods=['get'], url_path='patient/(?P<patient_id>[^/.]+)')
    def by_patient(self, request, patient_id=None):
        try:
            patient = Patient.objects.get(id=patient_id, created_by=request.user)
        except Patient.DoesNotExist:
            return Response(
                {"error": "Patient not found or you don't have permission to view it."},
                status=status.HTTP_404_NOT_FOUND
            )
        
        mappings = PatientDoctorMapping.objects.filter(patient=patient)
        serializer = self.get_serializer(mappings, many=True)
        return Response({
            "patient": PatientSerializer(patient).data,
            "doctors": serializer.data
        })

    def create(self, request, *args, **kwargs):
        try:
            return super().create(request, *args, **kwargs)
        except Exception as e:
            return Response(
                {"error": str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        if instance.patient.created_by != request.user:
            return Response(
                {"error": "You can only delete mappings for your own patients."},
                status=status.HTTP_403_FORBIDDEN
            )
        return super().destroy(request, *args, **kwargs)