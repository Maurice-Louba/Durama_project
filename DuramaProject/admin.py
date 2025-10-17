from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import (
    User, EmailOTP, Categorie, SubCategorie, TypeAttribut, Attribut, Etiquette,
    Produit, ImageProduit, ProduitVariable, ProduitVariableAttribut, ProduitVariableImage,
    AvisProduit, Panier, ContenuPanier, Commande, CommandeItem, Paiement, Livraison,Addresse,PromoCode,PromoCodeUsage,Favori
)

# ==============================
# USER
# ==============================
@admin.register(User)
class CustomUserAdmin(UserAdmin):
    list_display = ('first_name', 'last_name', 'email', 'is_active', 'is_staff','photo','is_superuser')
    ordering = ('email',)
    search_fields = ('email', 'first_name', 'last_name')
    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        ('Infos personnelles', {'fields': ('first_name', 'last_name', 'photo','phone_number', 'address', 'bio')}),
        ('Statut', {'fields': ('is_active', 'is_confirmed', 'is_staff', 'is_superuser')}),
        ('Permissions', {'fields': ('groups', 'user_permissions')}),
        ('Dates importantes', {'fields': ('last_login', 'date_joined')}),
    )
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'password1', 'password2', 'is_active', 'is_staff'),
        }),
    )


# ==============================
# CATEGORIES ET ATTRIBUTS
# ==============================
@admin.register(Categorie)
class CategorieAdmin(admin.ModelAdmin):
    list_display = ('nom', 'is_parent', 'created_at', 'updeated_at')
    search_fields = ('nom',)


@admin.register(SubCategorie)
class SubCategorieAdmin(admin.ModelAdmin):
    list_display = ('nom', 'categorie_principale', 'created_at', 'updated_at')
    search_fields = ('nom',)
    list_filter = ('categorie_principale',)


@admin.register(TypeAttribut)
class TypeAttributAdmin(admin.ModelAdmin):
    list_display = ('nom', 'created_at', 'updated_at')


@admin.register(Attribut)
class AttributAdmin(admin.ModelAdmin):
    list_display = ('valeur', 'typeAttribut', 'code_Couleur', 'created_at', 'updated_at')
    list_filter = ('typeAttribut',)


@admin.register(Etiquette)
class EtiquetteAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug', 'created_at', 'updated_at')
    search_fields = ('name',)


# ==============================
# PRODUITS ET VARIANTES
# ==============================
class ImageProduitInline(admin.TabularInline):
    model = ImageProduit
    extra = 1


class ProduitVariableInline(admin.TabularInline):
    model = ProduitVariable
    extra = 1


@admin.register(Produit)
class ProduitAdmin(admin.ModelAdmin):
    list_display = ('nom', 'type_produit', 'prix_fournisseur', 'prix_vente', 'quantite', 'etat_stock', 'status')
    search_fields = ('nom', 'sku')
    list_filter = ('type_produit', 'etat_stock', 'status', 'categorie')
    inlines = [ImageProduitInline, ProduitVariableInline]


@admin.register(ProduitVariable)
class ProduitVariableAdmin(admin.ModelAdmin):
    list_display = ('produit', 'prix_fournisseur', 'prix_vente', 'quantite', 'created_at')
    search_fields = ('produit__nom',)


@admin.register(ProduitVariableAttribut)
class ProduitVariableAttributAdmin(admin.ModelAdmin):
    list_display = ('produit_variable', 'attribut')
    list_filter = ('attribut',)


@admin.register(ProduitVariableImage)
class ProduitVariableImageAdmin(admin.ModelAdmin):
    list_display = ('produit_variable', 'image', 'created_at')


# ==============================
# PANIER & AVIS
# ==============================
@admin.register(AvisProduit)
class AvisProduitAdmin(admin.ModelAdmin):
    list_display = ('user', 'produit', 'note', 'created_at')
    search_fields = ('user__email', 'produit__nom')
    list_filter = ('note',)


@admin.register(Panier)
class PanierAdmin(admin.ModelAdmin):
    list_display = ('user', 'created_at', 'updated_at')


@admin.register(ContenuPanier)
class ContenuPanierAdmin(admin.ModelAdmin):
    list_display = ('panier', 'produit', 'produit_variable', 'quantite', 'is_variable')


# ==============================
# COMMANDES & PAIEMENTS
# ==============================
class CommandeItemInline(admin.TabularInline):
    model = CommandeItem
    extra = 1


@admin.register(Commande)
class CommandeAdmin(admin.ModelAdmin):
    list_display = ('numero', 'user', 'statut', 'montant_total', 'created_at')
    search_fields = ('numero', 'acheteur__email', 'vendeur__email')
    list_filter = ('statut',)
    inlines = [CommandeItemInline]


@admin.register(CommandeItem)
class CommandeItemAdmin(admin.ModelAdmin):
    list_display = ('commande', 'produit', 'produit_variable', 'quantite', 'prix_unitaire')


@admin.register(Paiement)
class PaiementAdmin(admin.ModelAdmin):
    list_display = ('commande', 'statut', 'methode', 'montant', 'date_paiement')


@admin.register(Livraison)
class LivraisonAdmin(admin.ModelAdmin):
    list_display = ('commande', 'transporteur', 'numero_suivi', 'date_expedition', 'date_livraison', 'statut')


# ==============================
# ADRESSES
# ==============================
@admin.register(Addresse)
class AddresseAdmin(admin.ModelAdmin):
    list_display = ('user', 'address', 'ville', 'pays', 'telephone', 'is_default', 'created_at', 'updated_at')
    search_fields = ('user__email', 'address', 'ville', 'pays', 'telephone')
    list_filter = ('pays', 'ville', 'is_default')
    readonly_fields = ('created_at', 'updated_at')

# ==============================
# CODES PROMO
# ==============================
class PromoCodeUsageInline(admin.TabularInline):
    model = PromoCodeUsage
    extra = 0
    readonly_fields = ('user', 'order', 'used_at', 'discount_applied')
    can_delete = False

@admin.register(PromoCode)
class PromoCodeAdmin(admin.ModelAdmin):
    list_display = ('code', 'discount_type', 'discount_value', 'is_active', 'start_date', 'end_date', 'current_uses', 'max_uses')
    search_fields = ('code',)
    list_filter = ('discount_type', 'is_active', 'start_date', 'end_date')
    inlines = [PromoCodeUsageInline]

@admin.register(PromoCodeUsage)
class PromoCodeUsageAdmin(admin.ModelAdmin):
    list_display = ('promo_code', 'user', 'order', 'discount_applied', 'used_at')
    search_fields = ('promo_code__code', 'user__email', 'order__numero')
    list_filter = ('used_at', 'promo_code')

@admin.register(Favori)
class FavoriAdmin(admin.ModelAdmin):
    list_display=('produit','user','created_at','updated_at')

