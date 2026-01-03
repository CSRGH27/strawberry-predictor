#!/usr/bin/env python3
"""
Analyse des récoltes à 0 kg par variété
"""
from .database import SessionLocal
from .models import HarvestRecord, Variety
from sqlalchemy import func
from datetime import date

def analyze_zeros():
    """
    Analyse détaillée des récoltes à 0 kg
    """
    db = SessionLocal()
    
    try:
        print("\n" + "="*80)
        print("🔍 ANALYSE DES RÉCOLTES À 0 KG")
        print("="*80)
        print("ℹ️  Note : Les dimanches sont exclus (normalement à 0)")
        print("="*80 + "\n")
        
        # ============================================================
        # STATISTIQUES GLOBALES
        # ============================================================
        print("📊 STATISTIQUES GLOBALES")
        print("="*80 + "\n")
        
        # Total de récoltes
        total_records = db.query(func.count(HarvestRecord.id)).scalar()
        
        # Total de zéros (SANS les dimanches)
        total_zeros = db.query(func.count(HarvestRecord.id)).filter(
            HarvestRecord.kg_produced == 0,
            func.extract('dow', HarvestRecord.date) != 0  # 0 = Dimanche
        ).scalar()
        
        # Pourcentage
        pct_zeros = (total_zeros / total_records * 100) if total_records > 0 else 0
        
        print(f"Total enregistrements : {total_records}")
        print(f"Récoltes à 0 kg       : {total_zeros}")
        print(f"Pourcentage           : {pct_zeros:.2f}%")
        
        # ============================================================
        # PAR VARIÉTÉ
        # ============================================================
        print("\n" + "="*80)
        print("📋 STATISTIQUES PAR VARIÉTÉ")
        print("="*80 + "\n")
        
        varieties = db.query(Variety).all()
        
        variety_stats = []
        
        for variety in varieties:
            # Total pour cette variété
            total_var = db.query(func.count(HarvestRecord.id)).filter(
                HarvestRecord.variety_id == variety.id
            ).scalar()
            
            # Zéros pour cette variété (SANS les dimanches)
            zeros_var = db.query(func.count(HarvestRecord.id)).filter(
                HarvestRecord.variety_id == variety.id,
                HarvestRecord.kg_produced == 0,
                func.extract('dow', HarvestRecord.date) != 0  # 0 = Dimanche
            ).scalar()
            
            # Pourcentage
            pct_var = (zeros_var / total_var * 100) if total_var > 0 else 0
            
            variety_stats.append({
                'name': variety.name,
                'total': total_var,
                'zeros': zeros_var,
                'pct': pct_var
            })
        
        # Afficher tableau
        print(f"{'Variété':<15} {'Total':<10} {'Zéros':<10} {'%':<10}")
        print("-" * 50)
        
        for stat in sorted(variety_stats, key=lambda x: x['pct'], reverse=True):
            print(f"{stat['name']:<15} {stat['total']:<10} {stat['zeros']:<10} {stat['pct']:<10.2f}%")
        
        # ============================================================
        # PAR JOUR DE SEMAINE
        # ============================================================
        print("\n" + "="*80)
        print("📅 ZÉROS PAR JOUR DE SEMAINE (hors dimanches)")
        print("="*80 + "\n")
        
        days_names = ['Lundi', 'Mardi', 'Mercredi', 'Jeudi', 'Vendredi', 'Samedi', 'Dimanche']
        
        # Zéros par jour pour chaque variété (SANS les dimanches)
        zeros_by_day = db.query(
            func.extract('dow', HarvestRecord.date).label('dow'),
            Variety.name,
            func.count(HarvestRecord.id).label('count')
        ).join(Variety).filter(
            HarvestRecord.kg_produced == 0,
            func.extract('dow', HarvestRecord.date) != 0  # 0 = Dimanche
        ).group_by('dow', Variety.name).order_by('dow', Variety.name).all()
        
        # Organiser par jour
        day_data = {}
        for dow, variety, count in zeros_by_day:
            day_idx = int(dow)
            if day_idx not in day_data:
                day_data[day_idx] = {}
            day_data[day_idx][variety] = count
        
        # Afficher
        for day_idx in range(7):
            if day_idx in day_data:
                print(f"\n{days_names[day_idx]} :")
                for variety, count in sorted(day_data[day_idx].items()):
                    print(f"  {variety:<15} : {count:3} zéros")
        
        # ============================================================
        # PAR ANNÉE
        # ============================================================
        print("\n" + "="*80)
        print("📆 ZÉROS PAR ANNÉE ET VARIÉTÉ")
        print("="*80 + "\n")
        
        zeros_by_year = db.query(
            HarvestRecord.year,
            Variety.name,
            func.count(HarvestRecord.id).label('count')
        ).join(Variety).filter(
            HarvestRecord.kg_produced == 0,
            func.extract('dow', HarvestRecord.date) != 0  # 0 = Dimanche
        ).group_by(HarvestRecord.year, Variety.name).order_by(
            HarvestRecord.year, Variety.name
        ).all()
        
        # Organiser par année
        year_data = {}
        for year, variety, count in zeros_by_year:
            if year not in year_data:
                year_data[year] = {}
            year_data[year][variety] = count
        
        # Afficher
        for year in sorted(year_data.keys()):
            print(f"\n{year} :")
            for variety, count in sorted(year_data[year].items()):
                print(f"  {variety:<15} : {count:3} zéros")
        
        # ============================================================
        # EXEMPLES DE ZÉROS SUSPECTS
        # ============================================================
        print("\n" + "="*80)
        print("🔍 EXEMPLES DE ZÉROS SUSPECTS (jours ouvrés)")
        print("="*80 + "\n")
        
        # Zéros en jours ouvrés (Lun-Ven)
        zeros_workdays = db.query(HarvestRecord).join(Variety).filter(
            HarvestRecord.kg_produced == 0,
            func.extract('dow', HarvestRecord.date).in_([1, 2, 3, 4, 5])  # Lun-Ven
        ).order_by(HarvestRecord.date.desc()).limit(20).all()
        
        if zeros_workdays:
            print(f"{'Date':<12} {'Jour':<10} {'Variété':<15} {'Plants':<10}")
            print("-" * 50)
            
            for record in zeros_workdays:
                day_name = days_names[record.date.weekday()]
                print(f"{record.date} {day_name:<10} {record.variety.name:<15} {record.plants_nbrs:<10}")
        else:
            print("✅ Aucun zéro suspect trouvé en jours ouvrés")
        
        # ============================================================
        # RECOMMANDATIONS
        # ============================================================
        print("\n" + "="*80)
        print("💡 RECOMMANDATIONS")
        print("="*80 + "\n")
        
        if pct_zeros < 2:
            print("✅ Peu de zéros (<2%) - Probablement légitimes (jours fériés)")
            print("   → Recommandation : GARDER les zéros")
        elif pct_zeros < 5:
            print("⚠️  Zéros modérés (2-5%) - À analyser au cas par cas")
            print("   → Recommandation : Filtrer les zéros en jours ouvrés uniquement")
        else:
            print("❌ Beaucoup de zéros (>5%) - Probablement des oublis de saisie")
            print("   → Recommandation : FILTRER tous les zéros en jours ouvrés")
        
        # Détail par variété
        print("\nPar variété :")
        for stat in sorted(variety_stats, key=lambda x: x['pct'], reverse=True):
            if stat['pct'] > 5:
                print(f"  ❌ {stat['name']:<15} : {stat['pct']:.1f}% de zéros → À filtrer")
            elif stat['pct'] > 2:
                print(f"  ⚠️  {stat['name']:<15} : {stat['pct']:.1f}% de zéros → À surveiller")
            else:
                print(f"  ✅ {stat['name']:<15} : {stat['pct']:.1f}% de zéros → OK")
        
        print("\n" + "="*80 + "\n")
        
    finally:
        db.close()


if __name__ == "__main__":
    analyze_zeros()