""" Serializers allow complex data such as querysets and model instances to be converted to native Python datatypes that can then be easily rendered into JSON,
 XML or other content types. Serializers also provide deserialization, allowing parsed data to be converted back into complex types, after first validating the incoming data. """


#Basic Serializer

from rest_framework import serializers
class CommentSerializer(serializers.Serializer):
    email = serializers.EmailField()
    content = serializers.CharField(max_length = 200)
    created = serializers.DateTimeField()


""" A ModelSerializer in DRF provides a shortcut that automatically generates a serializer class based on a Django model.
It behaves like a regular Serializer but provides additional features such as:

Automatic field generation from the model.
Model-based validators like unique_together.
Default implementations of .create() and .update() methods.
"""


#Models.py
from django.db import models

class Account(models.Model):
  user_id = models.IntegerField()
  account_name = models.CharField(max_lenght=50)
  user = models.CharField(max_length=100)
  created = models.DateTimeField(auto_now_add=True)


class AccountSerializer(serializers.ModelSerializer):
    class Meta:
        model = Account
        fields = ['user_id', 'account_name', 'user', 'created']




class SerializerName(serializers.ModelSerializer):
    class Meta:
        model = ModelName
        fields = List of Fields



#ListSerializer
"""The ListSerializer class provides the behavior for serializing and validating multiple objects at once. You won't typically need to use ListSerializer directly, but should instead simply pass many=True when instantiating a serializer.

When a serializer is instantiated and many=True is passed, a ListSerializer instance will be created. The serializer class then becomes a child of the parent ListSerializer

The following argument can also be passed to a ListSerializer field or a serializer that is passed many=True:"""

from rest_framework import serializers

class BookSerializer(serializers.Serializer):
    title = serializers.CharField()

class BookListSerializer(serializers.ListSerializer):
    child = BookSerializer()

    def create(self, validated_data):
        return [Book.objects.create(**item) for item in validated_data]



#Nested Serializers

from rest_framework import serializers

class AuthorSerializer(serializers.Serializer):
    name = serializers.CharField()

class BookSerializer(serializers.Serializer):
    title = serializers.CharField()
    author = AuthorSerializer()  # nested serializer





##Writable nested serializers¶
"""Although flat data structures serve to properly delineate between the individual entities in  service, 
there are cases where it may be more appropriate or convenient to use nested data structures.
Nested data structures are easy enough to work with if they're read-only - simply nest your serializer classes and you're good to go. However,
there are a few more subtleties to using writable nested serializers, due to the dependencies between the various model instances, 
and the need to save or delete multiple instances in a single action."""


class ToDoItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = ToDoItem
        fields = ['text', 'is_completed']

class ToDoListSerializer(serializers.ModelSerializer):
    items = ToDoItemSerializer(many=True, read_only=True)

    class Meta:
        model = ToDoList
        fields = ['title', 'items']
