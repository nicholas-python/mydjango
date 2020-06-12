from rest_framework import serializers
from ..models import Post, Comment
from taggit_serializer.serializers import TagListSerializerField, TaggitSerializer
from django.contrib.auth import get_user_model

class UserSerializer(serializers.ModelSerializer):
    blog_posts = serializers.PrimaryKeyRelatedField(many = True, queryset = Post.objects.all())
    
    class Meta:
        model = get_user_model()
        fields = ['id', 'username', 'blog_posts']

class CommentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Comment
        fields = ['name', 'email', 'body']
        
# class AuthorSerializer(serializers.ModelSerializer):
#     class Meta:
#         model = get_user_model()
#         fields = ['username', 'first_name', 'last_name', 'email']

class PostSerializer(TaggitSerializer, serializers.ModelSerializer):
    comments = CommentSerializer(many = True, read_only = True)
    tags = TagListSerializerField()
    author = serializers.ReadOnlyField(source = 'author.username')
    
    class Meta:
        model = Post
        fields = ['id', 'title', 'slug', 'author', 'body', 'comments', 'tags']