import numpy as np
import matplotlib.pyplot as plt

def plot_timeseries(df_monthly):
    """Affiche la courbe d'évolution temporelle du NDVI et NDMI."""
    fig, ax = plt.subplots(figsize=(14, 6))
    
    ax.plot(df_monthly.index, df_monthly['ndvi_median'], 'g-o', linewidth=2, markersize=6, label='NDVI Médian')
    ax.plot(df_monthly.index, df_monthly['ndmi_median'], 'b-s', linewidth=2, markersize=6, label='NDMI Médian')
    
    ax.set_title("Évolution mensuelle médiane - NDVI vs NDMI", fontsize=14)
    ax.set_xlabel("Date", fontsize=12)
    ax.set_ylabel("Valeur de l'indice", fontsize=12)
    ax.grid(True, linestyle='--', alpha=0.6)
    ax.legend(loc='lower right', fontsize=11)
    
    # On élargit la fenêtre Y car le NDMI peut devenir négatif
    ax.set_ylim(-0.4, 0.8) 
    
    plt.tight_layout()
    plt.show()

def plot_spatial_anomaly(ndmi_map, z_score, anomaly_mask, date_str):
    """Affiche côte à côte le NDMI brut et la carte des anomalies spatiales."""
    fig, axes = plt.subplots(1, 2, figsize=(16, 6))
    
    # Carte NDMI Brut
    im0 = axes[0].imshow(ndmi_map, cmap='RdYlBu', vmin=-0.2, vmax=0.6)
    axes[0].set_title(f"NDMI Brut\n{date_str}")
    axes[0].axis('off')
    fig.colorbar(im0, ax=axes[0], fraction=0.046, pad=0.04)
    
    # Carte Anomalies
    im1 = axes[1].imshow(z_score, cmap='RdYlBu', vmin=-3, vmax=3)
    # Surlignage des anomalies en rouge
    axes[1].imshow(np.where(anomaly_mask, 1, np.nan), cmap='Reds', vmin=0, vmax=1, alpha=0.8)
    axes[1].set_title(f"Anomalies Spatiales (Z-Score)\nRouge = Stress anormal")
    axes[1].axis('off')
    
    plt.tight_layout()
    plt.show()