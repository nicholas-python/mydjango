from django.shortcuts import render, get_object_or_404
from .models import Post, Comment
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from .forms import EmailPostForm, CommentForm
from django.core.mail import send_mail
from taggit.models import Tag
from django.db.models import Count
from django.contrib.postgres.search import SearchVector, SearchQuery, SearchRank, TrigramSimilarity
from .forms import SearchForm
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import ListView, FormView, CreateView, UpdateView, DeleteView
from django.urls import reverse_lazy
from django.utils.text import slugify


# Create your views here.

class PostListView(LoginRequiredMixin, ListView):
    queryset = Post.published.all()
    context_object_name = 'posts'
    paginate_by = 3
    template_name = 'blog/post/list.html'
    
    def get_queryset(self):
        qs = super().get_queryset()
        tag_slug = self.kwargs.get('tag_slug')
        
        if tag_slug:
            tag = get_object_or_404(Tag, slug = tag_slug)
            qs = qs.filter(tags__in =[tag])
            self.tag = tag
        else:
            self.tag = None
            
        return qs
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        if self.tag:
            context['tag'] = self.tag
            
        return context
    
class PostDetailView(LoginRequiredMixin, FormView):
    form_class = CommentForm
    template_name = 'blog/post/detail.html'
    
    def get_initial(self):
        pk = self.kwargs.get('pk')
        slug = self.kwargs.get('slug')
        self.post = get_object_or_404(Post, pk = pk, slug = slug)
        
        #List active comments
        self.comments = self.post.comments.filter(active = True)
        self.new_comment = None
        
        #List Similar posts
        post_tags_id = self.post.tags.values_list('id', flat = True)
        similar_posts = Post.published.filter(tags__in = post_tags_id).exclude(id = self.post.id)
        self.similar_posts = similar_posts.annotate(same_tags = Count('tags')).order_by('-same_tags', '-publish')[:4]
        
        return super().get_initial()
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['post'] = self.post
        context['comments'] = self.comments
        context['similar_posts'] = self.similar_posts
        
        return context
    
    def form_valid(self, form):
        new_comment = form.save(commit = False)
        new_comment.post = self.post
        new_comment.save()
        context = self.get_context_data()
        context['new_comment'] = new_comment
        
        return render(self.request, self.template_name, context= context)
   

class PostCreateView(CreateView):
    model = Post
    fields = ['title', 'body', 'tags']
    template_name = 'blog/post/post_form.html'
    
    def form_valid(self, form):
        form.instance.author = self.request.user
        form.instance.status = 'publihsed'
        form.instance.slug = slugify(form.instance.title, allow_unicode = True)
        
        return super().form_valid(form)     
   
class PostUpdateView(UpdateView):
    model = Post
    fields = ['title', 'body', 'tags']
    template_name = 'blog/post/post_form.html'
    query_pk_and_slug = True
    
    def get_queryset(self):
        qs = super().get_queryset()
        
        return qs.filter(author = self.request.user)
    
    def form_valid(self, form):
        form.instace.slug = slugify(form.instance.title, allow_unicode= True)
        
        return super().form_valid(form)
    
class PostDeleteView(DeleteView):
    model = Post
    template_name = 'blog/post/post_confirm_delete.html'
    success_url = reverse_lazy('blog:post_list')
    query_pk_and_slug = True
    
    def get_queryset(self):
        qs = super().get_queryset()
        
        return qs.filter(author = self.request.user)
        

@login_required
def post_share(request, post_id):
    post = get_object_or_404(Post, id=post_id, status='published')
    sent = False
    
    if request.method == 'POST':
        form = EmailPostForm(request.POST)
        if form.is_valid():
            cd = form.cleaned_data
            post_url = request.build_absolute_uri(post.get_absolute_url())
            subject = f"{cd['name']} recommends you read {post.title}"
            message = (f"Read {post.title} at {post_url}\n\n" f"{cd['name']} Comments: {cd['comments']}")
            send_mail(subject, message, 'django.patronus@gmail.com', [cd['to']])
            sent = True
    else:
        form = EmailPostForm()
    return render(request, 'blog/post/share.html', {'post': post, 'form': form, 'sent': sent})

@login_required
def post_search(request):
    if 'query' in request.GET:
        form = SearchForm(request.GET)
        if form.is_valid():
            query = form.cleaned_data['query']
            #results = Post.published.annotate(search = SearchVector('title', 'body').filter(search = query))
            #search_vector = SearchVector('title', 'body')
            #search_vector = SearchVector('title', weight = 'A') + SearchVector('body', weight = 'B')
            #search_query = SearchQuery(query)
            #results = Post.published.annotate(search = search_vector, rank = SearchRank(search_vector, search_query).filter(search = search_query).order_by('-rank'))
            #results = Post.published.annotate(rank = SearchRank(search_vector, search_query).filter(rank__gte = 0.3).order_by('-rank'))
            results = Post.published.annotate(similarity = TrigramSimilarity('title', query),).filter(similarity_gt = 0.1).order_by('-similarity')
        else:
            form = SearchForm()    
            query = None
            results = []
        
        return render(request, 'blog/post/search.html', {'form':form, 'query':query, 'results':results})
        