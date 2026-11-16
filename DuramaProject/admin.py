from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import (
    Addresse, Attribut, AvisProduit, Categorie, Commande, CommandeItem, ContenuPanier,
    DemandeAppelExpert, Etiquette, Favori, MessageContact, ImageProduit, Livraison, MateriauDevis, Paiement,
    Panier, Produit, ProduitVariable, ProduitVariableAttribut, ProduitVariableImage, ProjetDevis,
    PromoCode, PromoCodeUsage, SubCategorie, TypeAttribut, User, Vendeur,
)
from .services import annuler_commande

# NB : EmailOTP n'est volontairement pas dans l'admin (les codes de vérification sont secrets).


# ==============================
# USER
# ==============================
@admin.register(User)
class CustomUserAdmin(UserAdmin):
    list_display = ('email', 'first_name', 'last_name', 'is_active', 'is_confirmed', 'is_staff', 'is_superuser', 'date_joined')
    list_filter = ('is_active', 'is_confirmed', 'is_staff', 'is_superuser')
    ordering = ('email',)
    search_fields = ('email', 'first_name', 'last_name', 'phone_number')
    readonly_fields = ('last_login', 'date_joined')
    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        ('Infos personnelles', {'fields': ('first_name', 'last_name', 'photo', 'phone_number', 'address', 'bio')}),
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
    list_display = ('nom', 'gros_categorie', 'is_parent', 'created_at', 'updeated_at')
    list_filter = ('gros_categorie', 'is_parent')
    search_fields = ('nom',)


@admin.register(SubCategorie)
class SubCategorieAdmin(admin.ModelAdmin):
    list_display = ('nom', 'categorie_principale', 'created_at', 'updated_at')
    search_fields = ('nom',)
    list_filter = ('categorie_principale',)
    list_select_related = ('categorie_principale',)


@admin.register(TypeAttribut)
class TypeAttributAdmin(admin.ModelAdmin):
    list_display = ('nom', 'created_at', 'updated_at')
    search_fields = ('nom',)


@admin.register(Attribut)
class AttributAdmin(admin.ModelAdmin):
    list_display = ('valeur', 'typeAttribut', 'code_Couleur', 'created_at', 'updated_at')
    list_filter = ('typeAttribut',)
    search_fields = ('valeur',)
    list_select_related = ('typeAttribut',)


@admin.register(Etiquette)
class EtiquetteAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug', 'created_at', 'updated_at')
    search_fields = ('name',)
    prepopulated_fields = {'slug': ('name',)}


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
    list_display = (
        "nom",
        "vendeur",
        "categorie",
        "type_produit",
        "prix_vente",
        "prix_promo",
        "quantite",
        "etat_stock",
        "status",
        "est_publie",
    )
    list_editable = ("quantite", "etat_stock", "est_publie")
    search_fields = ('nom', 'sku', 'slug')
    list_filter = ('type_produit', 'etat_stock', 'status', 'est_publie', 'categorie', 'vendeur')
    list_select_related = ('vendeur', 'categorie')
    readonly_fields = ('slug', 'vues', 'nombres_ventes', 'created_at', 'updated_at')
    inlines = [ImageProduitInline, ProduitVariableInline]


@admin.register(ProduitVariable)
class ProduitVariableAdmin(admin.ModelAdmin):
    list_display = ('produit', 'prix_fournisseur', 'prix_vente', 'prix_promo', 'quantite', 'created_at')
    search_fields = ('produit__nom',)
    list_select_related = ('produit',)


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
    search_fields = ('user__email', 'produit__nom', 'texte')
    list_filter = ('note',)
    list_select_related = ('user', 'produit')


@admin.register(Panier)
class PanierAdmin(admin.ModelAdmin):
    list_display = ('user', 'actif', 'created_at', 'updated_at')
    list_filter = ('actif',)
    search_fields = ('user__email',)
    list_select_related = ('user',)


@admin.register(ContenuPanier)
class ContenuPanierAdmin(admin.ModelAdmin):
    list_display = ('panier', 'produit', 'produit_variable', 'quantite', 'is_variable')
    search_fields = ('panier__user__email', 'produit__nom')
    list_select_related = ('panier__user', 'produit', 'produit_variable')


# ==============================
# COMMANDES & PAIEMENTS
# ==============================
class CommandeItemInline(admin.TabularInline):
    # Lignes figées : une commande passée ne se modifie pas à la main (sinon totaux incohérents)
    model = CommandeItem
    extra = 0
    can_delete = False
    readonly_fields = ('produit', 'produit_variable', 'quantite', 'prix_unitaire')

    def has_add_permission(self, request, obj=None):
        return False


@admin.action(description="Annuler les commandes sélectionnées (remet le stock)")
def action_annuler_commandes(modeladmin, request, queryset):
    for commande in queryset.exclude(statut='annulee'):
        annuler_commande(commande)


@admin.register(Commande)
class CommandeAdmin(admin.ModelAdmin):
    list_display = ('numero', 'user', 'statut', 'montant_total', 'created_at')
    # (avant : 'acheteur__email' / 'vendeur__email' -> la recherche plantait)
    search_fields = ('numero', 'user__email', 'adresse_livraison')
    list_filter = ('statut', 'created_at')
    list_select_related = ('user',)
    readonly_fields = ('numero', 'user', 'panier', 'total_produits', 'montant_total', 'created_at', 'updated_at')
    inlines = [CommandeItemInline]
    actions = [action_annuler_commandes]
    date_hierarchy = 'created_at'

    def save_model(self, request, obj, form, change):
        if change and 'statut' in form.changed_data and obj.statut == 'annulee':
            # Passer par le service pour remettre le stock
            obj.statut = form.initial.get('statut', obj.statut)
            super().save_model(request, obj, form, change)
            annuler_commande(obj)
            return
        super().save_model(request, obj, form, change)
        if 'frais_livraison' in form.changed_data:
            obj.calculer_totaux()


@admin.register(CommandeItem)
class CommandeItemAdmin(admin.ModelAdmin):
    list_display = ('commande', 'produit', 'produit_variable', 'quantite', 'prix_unitaire')
    search_fields = ('commande__numero', 'produit__nom')
    list_select_related = ('commande', 'produit', 'produit_variable')
    readonly_fields = ('commande', 'produit', 'produit_variable', 'quantite', 'prix_unitaire')


@admin.register(Paiement)
class PaiementAdmin(admin.ModelAdmin):
    list_display = ('commande', 'statut', 'methode', 'montant', 'transaction_id', 'date_paiement')
    list_filter = ('statut', 'methode')
    search_fields = ('commande__numero', 'transaction_id', 'commande__user__email')
    list_select_related = ('commande',)
    readonly_fields = ('montant',)


@admin.register(Livraison)
class LivraisonAdmin(admin.ModelAdmin):
    list_display = ('commande', 'transporteur', 'numero_suivi', 'date_expedition', 'date_livraison', 'statut')
    search_fields = ('commande__numero', 'numero_suivi', 'transporteur')
    list_select_related = ('commande',)


# ==============================
# ADRESSES
# ==============================
@admin.register(Addresse)
class AddresseAdmin(admin.ModelAdmin):
    list_display = ('user', 'address', 'ville', 'pays', 'telephone', 'is_default', 'created_at', 'updated_at')
    search_fields = ('user__email', 'address', 'ville', 'pays', 'telephone')
    list_filter = ('pays', 'ville', 'is_default')
    list_select_related = ('user',)
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
    readonly_fields = ('current_uses',)
    filter_horizontal = ('eligible_users', 'target_products', 'target_categories')
    inlines = [PromoCodeUsageInline]


@admin.register(PromoCodeUsage)
class PromoCodeUsageAdmin(admin.ModelAdmin):
    list_display = ('promo_code', 'user', 'order', 'discount_applied', 'used_at')
    search_fields = ('promo_code__code', 'user__email', 'order__numero')
    list_filter = ('used_at', 'promo_code')


@admin.register(Favori)
class FavoriAdmin(admin.ModelAdmin):
    list_display = ('produit', 'user', 'created_at', 'updated_at')
    search_fields = ('produit__nom', 'user__email')
    list_select_related = ('produit', 'user')


# ==============================
# DEVIS
# ==============================
class MateriauDevisInline(admin.TabularInline):
    model = MateriauDevis
    extra = 0
    readonly_fields = ("nom", "produit", "quantite", "unite", "prix_unitaire", "prix_total")
    can_delete = False


@admin.register(MateriauDevis)
class MateriauDevisAdmin(admin.ModelAdmin):
    list_display = ("nom", "projet", "quantite", "unite", "prix_unitaire", "prix_total")
    list_filter = ("unite",)
    search_fields = ("nom",)
    readonly_fields = ("prix_total",)
    ordering = ("nom",)


@admin.register(ProjetDevis)
class ProjetDevisAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "nom_projet",
        "user",
        "ville",
        "type_projet",
        "surface",
        "nombre_etages",
        "structure",
        "toiture",
        "prix_estime",
        "created_at",
    )
    list_filter = ("type_projet", "structure", "finition", "toiture", "objectif")
    search_fields = ("nom_projet", "ville", "quartier", "user__email")
    readonly_fields = ("prix_estime", "created_at", "updated_at")
    list_select_related = ("user",)
    ordering = ("-created_at",)
    inlines = [MateriauDevisInline]


# ==============================
# APPELS EXPERT
# ==============================
@admin.register(DemandeAppelExpert)
class DemandeAppelExpertAdmin(admin.ModelAdmin):
    list_display = ("nom", "telephone", "sujet", "disponibilite", "date_appel", "statut", "created_at")
    list_filter = ("statut", "disponibilite")
    search_fields = ("nom", "email", "telephone", "sujet")
    list_select_related = ("user",)
    readonly_fields = ("user", "date_traitement", "created_at", "updated_at")
    date_hierarchy = "created_at"


# ==============================
# VENDEURS
# ==============================
@admin.register(Vendeur)
class VendeurAdmin(admin.ModelAdmin):
    list_display = (
        "nom_boutique",
        "telephone",
        "ville",
        "pays",
        "est_verifie",
        "actif",
        "created_at",
    )

    search_fields = (
        "nom_boutique",
        "telephone",
        "email_commercial",
        "ville",
    )

    list_filter = (
        "est_verifie",
        "actif",
        "ville",
        "pays",
    )

    prepopulated_fields = {
        "slug": ("nom_boutique",)
    }



# ==============================
# MESSAGES DE CONTACT
# ==============================
@admin.register(MessageContact)
class MessageContactAdmin(admin.ModelAdmin):
    list_display = ('sujet', 'email', 'nom', 'telephone', 'traite', 'created_at')
    list_filter = ('traite', 'created_at')
    search_fields = ('sujet', 'email', 'nom', 'message')
    readonly_fields = ('user', 'nom', 'email', 'telephone', 'sujet', 'message', 'created_at')
    list_editable = ('traite',)
    actions = ['marquer_traites']

    @admin.action(description="Marquer comme traités")
    def marquer_traites(self, request, queryset):
        queryset.update(traite=True)
