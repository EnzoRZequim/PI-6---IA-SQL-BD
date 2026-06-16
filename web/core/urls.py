

from django.urls import path
from . import views

urlpatterns = [
    
    path("login/",  views.login_view,  name="login"),
    path("logout/", views.logout_view, name="logout"),

   
    path("",              views.selecionar_banco, name="selecionar_banco"),
    path("banco/<nome>/", views.selecionar_banco, name="usar_banco"),

    
    path("chat/",         views.chat_view,    name="chat"),
    path("chat/query/",   views.chat_query,   name="chat_query"),

    
    path("admin/",                              views.admin_panel,            name="admin_panel"),
    path("admin/usuarios/criar/",               views.admin_criar_usuario,    name="admin_criar_usuario"),
    path("admin/usuarios/<int:uid>/cargo/",     views.admin_atribuir_cargo,   name="admin_atribuir_cargo"),
    path("admin/usuarios/<int:uid>/deletar/",   views.admin_deletar_usuario,  name="admin_deletar_usuario"),
    path("admin/cargos/criar/",                 views.admin_criar_cargo,      name="admin_criar_cargo"),
    path("admin/cargos/<int:cid>/deletar/",     views.admin_deletar_cargo,    name="admin_deletar_cargo"),
    path("admin/cargos/<int:cid>/permissoes/",  views.admin_permissoes_cargo, name="admin_permissoes_cargo"),
]
