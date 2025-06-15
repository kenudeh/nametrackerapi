from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.shortcuts import get_object_or_404
from .models import Name
from .serializers import NameSerializer

class NameListAPIView(APIView):
    def get(self, request):
        names = Name.objects.all()
        serializer = NameSerializer(names, many=True)
        return Response(serializer.data)

class NameDetailAPIView(APIView):
    def get(self, request, pk):
        name = get_object_or_404(Name, pk=pk)
        serializer = NameSerializer(name)
        return Response(serializer.data)

class NameCreateAPIView(APIView):
    def post(self, request):
        serializer = NameSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class NameUpdateAPIView(APIView):
    def patch(self, request, pk):
        name = get_object_or_404(Name, pk=pk)
        serializer = NameSerializer(name, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class NameDeleteAPIView(APIView):
    def delete(self, request, pk):
        name = get_object_or_404(Name, pk=pk)
        name.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)