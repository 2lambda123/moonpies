"""Moonpies plotting module."""
from datetime import datetime
from pathlib import Path
from multiprocessing import Process
import numpy as np
from scipy import stats
import pandas as pd
import matplotlib as mpl
import matplotlib.pyplot as plt
import seaborn as sns
from moonpies import moonpies as mp
from moonpies import config
from moonpies import plotting as mplt
import aggregate as agg

# Plot helpers
CFG = config.Cfg(seed=1)
DATE = datetime.now().strftime("%y%m%d")
FIGDIR = Path(CFG.figs_path) / f'{DATE}_v{CFG.version}'
DATEDIR = '../out/230202'
CORDER = np.array(['Faustini', 'Haworth', 'Shoemaker', 'Cabeus B', 
                   "Idel'son L",'Amundsen','Cabeus','de Gerlache',
                   'Slater','Sverdrup','Wiechert J','Shackleton'])
mplt.reset_plot_style()  # Sets Moonpies style

# Helpers
def _save_or_show(fig, ax, fsave, figdir, version='', **kwargs):
    """Save figure or show fig and return ax."""
    if fsave:
        fsave = Path(figdir) / Path(fsave)  # Prepend path
        # Append version if not already in figdir or fsave
        if version not in fsave.as_posix():
            fsave = fsave.with_name(f'{fsave.stem}_{version}{fsave.suffix}')
        fsave.parent.mkdir(parents=True, exist_ok=True)  # Make dir if doesn't exist
        fig.savefig(fsave, bbox_inches='tight', **kwargs)
        print(f'Figure saved to {fsave}')
    plt.show()
    return ax


def _generate_all():
    """Produce all figures in figdir in parallel with default args."""
    # Get all functions in this module
    funcs = [obj for name, obj in globals().items() if callable(obj) and 
                obj.__module__ == __name__ and name[0] != '_']
    
    # Run each with defaults in its own process
    print(f'Starting {len(funcs)} plots...')
    procs = [Process(target=func) for func in funcs]
    _ = [p.start() for p in procs]
    _ = [p.join() for p in procs]
    print(f'All plots written to {FIGDIR}')


def _get_datedir(cfg):
    """Get datedir from cfg."""
    outdir = Path(cfg.data_path).parents[1] / 'out'
    subdirs = [p for p in outdir.iterdir() if p.is_dir()]
    for subdir in subdirs[::-1]:
        if any(subdir.glob('layers.csv')):
            datedir = subdir
            break
    else:
        raise FileNotFoundError('No datedir found. Please specify.')
    return datedir


def _load_aggregated(cfg, datedir, flatten=True, nruns=True):
    """Load aggregated data."""
    # If no datedir, guess latest date folder in outdir that has layers.csv
    if not datedir:  
        datedir = _get_datedir(cfg)
    print(f'Loading aggregated data from {datedir}')
    return agg.read_agg_dfs(Path(datedir), flatten, nruns)


def compare_violin(fsave='bsed_violin.pdf', figdir=FIGDIR, cfg=CFG, datedir=DATEDIR, 
                corder=CORDER, run_names=('moonpies', 'no_bsed'), rename=('Yes', 'No'), title='Ballistic\nSedimentation\n'):
    """Plot paired violins comparing ice in two runs grouped by crater."""
    mplt.reset_plot_style()
    clist = mp.get_crater_basin_list(cfg).set_index('cname').loc[corder]
    labels = [c+f'\n{lat:.1f}°' for c, lat in zip(corder, clist.lat.values)]
    
    # Load and clean aggregated runs data
    datedir = Path(datedir)
    _, runs, nruns = _load_aggregated(cfg, datedir, flatten=True, nruns=True)
    runs = agg.rename_runs(runs, run_names, rename)
    runs.loc[runs['total ice'] < 1, 'total ice'] = np.nan
    runs['log ice'] = np.log10(runs['total ice'])

    # Plot
    fig, ax = plt.subplots(figsize=(8, 2.5))

    ax.fill_between([2.5, 7.5], [-1, -1], [4, 4], color='tab:gray', alpha=0.5)
    ax.fill_between([9.5, 12.5], [-1, -1], [4, 4], color='tab:gray', alpha=0.5)
    ax = sns.violinplot(x='coldtrap', y='log ice', hue='runs', 
                        hue_order=rename[::-1], data=runs, split=True, cut=0,
                        inner='quartiles', palette='Set2', order=corder,
                        scale='count', scale_hue=False, ax=ax, width=0.95)

    # Plot a specific value on the violin plot
    # ax.plot(['Haworth'], [1.5], 'ro')
    ax.set_xticklabels(labels, rotation=30, fontsize=9)
    ax.tick_params('x', direction='out', top=False)
    ax.set_ylabel('Total ice thickness [m]', labelpad=-0.8)
    ax.set_yticks([0, 1, 2, 3])
    ax.set_yticklabels(10**ax.get_yticks())
    ax.set_xlabel('')
    
    ymin = -0.45
    ax.set_ylim(ymin, 3)
    ax.set_xlim(-0.5, 11.75)
    ax.annotate('Pre/Early Nectarian', (-0.4, ymin+0.1))
    ax.annotate('Late Nectarian', (2.6, ymin+0.1))
    ax.annotate('Imbrian', (7.6, ymin+0.1))
    ax.annotate('Eratosthenian', (9.6, ymin+0.1))
    

    title = title + f'({nruns} runs)'
    leg = plt.legend(loc='upper right', borderaxespad=0.25, title_fontsize=9, fontsize=9, ncol=2, 
                     columnspacing=0.5, handletextpad=0.2, title=title)
    leg.get_title().set_multialignment('center')

    version = mplt.plot_version(cfg, loc='ur', xyoff=(0.01, -0.4), ax=ax, fontsize=8)
    return _save_or_show(fig, ax, fsave, figdir, version)


def crater_basin_ages(fsave='crater_basin_ages.pdf', figdir=FIGDIR, cfg=CFG):
    """
    Plot crater basin ages.

    :Authors:
        A. Madera, C. J. Tai Udovicic
    """
    mplt.reset_plot_style()
    sns.set_style("ticks", {'ytick.direction': 'in'})
    
    # Plot params
    fs_large = 12
    df = mp.get_crater_basin_list(cfg)
    ej_distances = mp.get_coldtrap_dists(df, cfg)
    thick = mp.get_ejecta_thickness_matrix(df, ej_distances, cfg)
    for i, row in df.iterrows():
        if thick[i].max() > 0 and row.isbasin:
            # print(f'{row.cname} hits at {row.age}')
            df.loc[i, 'cname'] = f'*{row.cname}'

    dc = df.loc[~df.isbasin].set_index('cname')
    db = df.loc[df.isbasin].set_index('cname')

    nec_ga = db.loc["*Nectaris", "age"] / 1e9  # Necarian
    imb_ga = db.loc["Imbrium", "age"] / 1e9 # Imbrian
    era_ga = 3.2  # Eratosthenian
    cop_ga = 1.1  # Copernican
    eras = {
        'pNe.': dict(xmin=4.5, xmax=nec_ga, facecolor='#253494', alpha=0.3),
        'Ne.': dict(xmin=nec_ga, xmax=imb_ga, facecolor='#2c7fb8', alpha=0.4),
        'Im.': dict(xmin=imb_ga, xmax=era_ga, facecolor='#41b6c4', alpha=0.3),
        'Era.': dict(xmin=era_ga, xmax=cop_ga, facecolor='#a1dab4', alpha=0.3)
    }

    # Figure and main crater axis
    fig, axc = plt.subplots(figsize=(7.2, 9.5))

    # Make basin inset
    left, bottom, width, height = [0.53, 0.35, 0.35, 0.5]
    axb = fig.add_axes([left, bottom, width, height])

    for ax, df in zip([axc, axb], [dc, db]):
        # Plot crater / basin ages
        df = df.sort_values(['age', 'age_upp'])
        age, low, upp = df[["age", "age_low", "age_upp"]].values.T / 1e9
        ax.errorbar(age, df.index, xerr=(low, upp), fmt='ko', ms=5, capsize=4, 
                    capthick=2)
        ax.invert_xaxis()
        if ax == axc:
            ax.set_ylabel('Craters', fontsize=fs_large, labelpad=-0.2)
            ax.set_xlabel('Absolute Model Ages [Ga]', fontsize=fs_large)
            ax.set_xlim(4.4, 1.4)
            ax.tick_params(axis='y')
        else:
            ax.set_title('Basins', pad=3, fontsize=fs_large)
            ax.set_xlabel('Absolute Model Ages [Ga]')
            ax.set_xlim(4.35, 3.79)

        # Add Chronological Periods
        for era, params in eras.items():
            ax.axvspan(**params, edgecolor='none')
            if ax == axb and era == 'Era.':
                continue
            x = max(params['xmax'], ax.get_xlim()[1])
            y = ax.get_ylim()[0]
            ax.annotate(era, xy=(x, y), xycoords='data', fontsize=fs_large, 
                        weight='bold', ha='right', va='bottom')
    mplt.reset_plot_style()
    version = mplt.plot_version(cfg, loc='lr', xyoff=(0.01, -0.1), ax=axc)
    return _save_or_show(fig, axc, fsave, figdir, version)


def crater_scaling(fsave='crater_scaling.pdf', figdir=FIGDIR, cfg=CFG):
    """
    Plot crater scaling from final diameter to impactor diameter.

    :Authors:
        K. M. Luchsinger, C. J. Tai Udovicic
    """
    mplt.reset_plot_style()

    speed = 20000  # [m/s]
    dfb = mp.read_basin_list(cfg)
    labels = {
        'c': 'C: Small simple craters (Prieur et al., 2017)', 
        'd': 'D: Large simple craters (Collins et al., 2005)', 
        'e': 'E: Complex craters (Johnson et al., 2016)',
        'f': 'F: Basins (Johnson et al., 2016)'}
    
    # TODO: fix regimes to be continuous in impactor space. 
    # Proposal: change c_min to 250 (i_diam=3) and e_min to 19e3 (i_diam=750)
    new_regimes = {
        # regime: (rad_min, rad_max, step, sfd_slope)
        'a': (0, 0.01, None, None),  # micrometeorites (<1 mm)
        'b': (0.01, 3, 1e-4, -3.7),  # small impactors (Cannon: 10 mm - 3 m)
        'c': (250, 1.5e3, 1, -3.82),  # simple craters, steep sfd (Cannon: 100 m - 1.5 km)
        'd': (1.5e3, 15e3, 1e2, -1.8),  # simple craters, shallow sfd (Cannon: 1.5 km - 15 km)
        'e': (19e3, 300e3, 1e3, -1.8),  # complex craters, shallow sfd (Cannon: 15 km - 300 km)
    }
    cdict = cfg.to_dict()
    cdict['impact_regimes'] = new_regimes
    alt_cfg = config.Cfg(**cdict)

    # Plot regimes c - e
    fig, ax = plt.subplots(figsize=(7.2, 5.5))
    for i, rcfg in enumerate([cfg, alt_cfg]):
        for regime, (dmin, dmax, *_) in rcfg.impact_regimes.items():
            if regime in ('a', 'b'):
                continue
            diams = np.geomspace(dmin, dmax, 2)
            lengths = mp.diam2len(diams, speed, regime, rcfg)
            label = labels[regime] if i == 0 else ''
            fmt = '-' if i == 0 else 'rx'
            ax.loglog(diams/1e3, lengths, fmt, label=label)

    # Plot individual basins
    basin_lengths = mp.diam2len(dfb.diam, speed, 'f', cfg)
    ax.loglog(dfb.diam/1e3, basin_lengths, 'k+', label=labels['f'])
    ax.set_ylim(0.3, None)
    ax.set_xlabel('Crater Diameter [km]')
    ax.set_ylabel('Impactor Diameter [km]')
    ax.set_title(f'Crater to Impactor Scaling (with $v$={speed/1e3} km/s)')

    # Plot transitions
    ax.axvline(cfg.simple2complex/1e3, c='k', ls='--')
    ax.annotate('Simple to complex', xy=(cfg.simple2complex/1e3, 1), ha='right', rotation=90)
    ax.axvline(cfg.complex2peakring/1e3, c='k', ls='--')
    ax.annotate('Complex to basin', xy=(cfg.complex2peakring/1e3, 1), ha='right', rotation=90)
    ax.legend(title='Regime', loc='upper left', fontsize=9)
    version = mplt.plot_version(cfg, loc='ll', ax=ax)
    return _save_or_show(fig, ax, fsave, figdir, version)


def distance_bsed(fsave='distance_bsed.pdf', figdir=FIGDIR, cfg=CFG):
    """
    Plot distance between basins and craters.

    :Authors:
        K. M. Luchsinger, C. J. Tai Udovicic
    """
    mplt.reset_plot_style()
    cdict = cfg.to_dict() 
    cdict['ej_threshold'] = -1
    cfg = config.Cfg(**cdict)

    # Ries data
    fries = Path(cfg.data_path) / 'horz_etal_1983_table2_fig19.csv'
    ries = pd.read_csv(fries, usecols=[1, 2, 4, 5])
    ries.columns = ['dist_km', 'dist_crad', 'wt_pct', 'mixing_ratio']

    # Get mixing ratio and vol frac
    coldtraps = np.array(cfg.coldtrap_names)  # Order of 2nd axis of dists
    df = mp.get_crater_basin_list(cfg)
    dists = mp.get_coldtrap_dists(df, cfg)
    thick = mp.get_ejecta_thickness_matrix(df, dists, cfg)
    mixing_ratio = mp.get_mixing_ratio_oberbeck(dists, cfg)
    
    dist_m = ries.dist_km.values * 1e3
    mr_oberbeck = mp.get_mixing_ratio_oberbeck(dist_m, cfg)
    fig, axs = plt.subplots(2, figsize=(7.2, 9))
    
    # Ries
    ax = axs[0]
    ax.loglog(dist_m, ries.mixing_ratio, 'ro', label='Ries')
    ax.loglog(dist_m, mr_oberbeck, 'k--', label='Oberbeck')
    ax.set_title("Mixing ratio with distance from crater")
    ax.set_xlabel("Distance [Crater Radii]")
    ax.set_ylabel("Mixing ratio [target:ejecta]")

    # Mixing ratio of craters
    for coldtrap in coldtraps[:6]:
        idx = df[df.cname == coldtrap].index[0]
        # dist_crad = dists/df.rad.values[:, None]
        # ax.plot(dist_crad[idx], 1-vol_frac[idx], 'x', label=coldtrap)
        ax.loglog(dists[idx], mixing_ratio[idx], 'x', label=coldtrap)
    ax.legend()
    
    # Amundsen to Haworth, Shoemaker, Faustini
    aidx = df[df.cname == 'Amundsen'].index[0]
    hidx = np.argmax(coldtraps == 'Haworth')
    sidx = np.argmax(coldtraps == 'Shoemaker')
    fidx = np.argmax(coldtraps == 'Faustini')
    dfc = df[~df.isbasin]
    xmax = np.nanmax(dists[dfc.index])
    bsed_depths = -thick*mixing_ratio
    ax = axs[1]
    ax.plot(dists[0], thick[0], label="Ejecta thickness")
    ax.plot(dists, thick, 'x', c='tab:blue')
    ax.axhline(0, c='k', label='Surface', zorder=10)
    ax.plot(dists[0], bsed_depths[0], label="Ballistic Sed. Mixing Region")
    ax.plot(dists, bsed_depths, '+', c='tab:orange')
    
    ax.axvline(dists[aidx,fidx], color='red', ls='--', label='Amundsen->Faustini')
    ax.axvline(dists[aidx,sidx], color='orange', ls='--', label='Amundsen->Shoemaker')
    ax.axvline(dists[aidx,hidx], color='gold', ls='--', label='Amundsen->Haworth')
    ax.set_xlim(0, xmax)
    ax.legend()
    ax.set_title("Ballistic Sedimentation Mixing Region")
    ax.set_xlabel("Distance [m]")
    ax.set_ylabel("Thickness [m]")
    version = mplt.plot_version(cfg, loc='lr', ax=ax)
    return _save_or_show(fig, ax, fsave, figdir, version)


def ejecta_bsed(fsave='ejecta_bsed.pdf', figdir=FIGDIR, cfg=CFG):
    """
    Plot ejecta thickness and ballistic mixing depth.
    """
    mplt.reset_plot_style()
    s2c = cfg.simple2complex / 2
    c2p = cfg.complex2peakring / 2
    radii = {
        's': np.geomspace(1e2, s2c-10, 10),
        'c': np.geomspace(s2c+10, c2p-10, 10),
        'b': np.geomspace(c2p+10, 6.6e5, 10)}
    labels = {'s': 'Simple crater', 'c': 'Complex crater', 'b': 'Basin'}
    ms = {'s': '^', 'c': 's', 'b': 'o'}
    colors = ['tab:blue', 'tab:orange', 'tab:green', 'tab:gray']
    dist_arr = np.array([1e3, 1e4, 1e5, 1e6])

    # Plot
    fig, axs = plt.subplots(2, sharex=True, figsize=(5, 10))
    fig.subplots_adjust(hspace=0.05)
    for dist, color in zip(dist_arr, colors):
        for ctype, rads in radii.items():
            dists = np.ones(len(rads))*dist
            with np.errstate(invalid='ignore'):
                thick = mp.get_ejecta_thickness(dists, rads, cfg)
            thick[dist<rads] = 0
            label = None
            if color == 'tab:blue':
                label = f'{labels[ctype]} (D=({2*rads[0]/1e3:.1f}, {2*rads[-1]/1e3:.0f}) km)'
            ax = axs[0]
            ax.loglog(rads, thick, ms[ctype], c=color, label=label)
            ax.set_ylabel('Ejecta Thickness [km]')
            ax.legend(fontsize=9)

            ax = axs[1]
            mixing_ratio = mp.get_mixing_ratio_oberbeck(dists, cfg)
            bsed = thick*mixing_ratio
            ax.loglog(rads, bsed, ms[ctype], c=color, label=label)
            ax.set_ylabel('Ballistic Mixing Depth [km]')
            ax.set_xlabel('Radius [km]')
            ax.set_xlim(50, 7e5)
            ax.legend(fontsize=9)
            if ctype == 's':
                axs[0].annotate(f'Distance={dist/1e3:.0f} km', (rads[0]-40, thick[0]), rotation=47)
                axs[1].annotate(f'Distance={dist/1e3:.0f} km', (rads[0]-40, bsed[0]), rotation=47)
    version = mplt.plot_version(cfg, loc='lr', xyoff=(0.01, -0.15), ax=axs[1])
    return _save_or_show(fig, ax, fsave, figdir, version)


def kde_layers(fsave='kde_layers.pdf', figdir=FIGDIR, cfg=CFG, datedir=DATEDIR, 
               coldtraps=("Faustini", "Haworth", "Amundsen", "Cabeus", 
               "de Gerlache", "Slater"), run_names=('moonpies', 'no_bsed'), 
               rename=('Yes', 'No')):
    """
    Plot KDE of ejecta thickness and ballistic mixing depth.
    """
    import patchworklib as pw
    pw.overwrite_axisgrid()
    pw.param['margin'] = 0.05
    mplt.reset_plot_style()
    custom_params = {"axes.spines.right": False, "axes.spines.top": False}
    sns.set_theme(style="ticks", rc=custom_params)
    pal = sns.color_palette()
    mypal = [pal[1], pal[0]]
    xlim = (0.05, 150)
    ylim = (1, 800)
    skip = 300  # skip this many points for each coldtrap (for faster kde)

    # Clean layer data
    layers, _, _ = _load_aggregated(cfg, datedir)
    layers = agg.rename_runs(layers, run_names, rename)
    layers = layers.round({'depth': 1, 'ice': 1})
    layers.loc[layers['ice'] < 0.1, 'ice'] = np.nan
    layers.loc[layers['depth'] < 0.1, 'depth'] = np.nan
    layers.dropna(inplace=True)
    
    layers['depth_top'] = layers['depth'] - layers['ice']
    layers['depth_top'] = layers['depth_top'].clip(lower=0.1)

    # Make seaborn jointgrids then put together with patchwork
    jgs = []
    for i, coldtrap in enumerate(coldtraps):
        df = layers[(layers.coldtrap==coldtrap)]
        if len(df) > 1000:
            df = df.iloc[::skip]
        # df = layers[(layers.coldtrap==coldtrap)].iloc[::skip]
        jg = sns.JointGrid(space=0, height=2.5)
        jg.ax_joint.annotate(f'{coldtrap}', xy=(0.5, 0.98), ha='center', va='top', xycoords='axes fraction')
        g = sns.kdeplot(x='ice', y='depth', hue='runs', hue_order=rename[::-1], data=df, log_scale=True, 
                    palette=mypal[::-1], bw_adjust=1.5, thresh=0.2, levels=8, common_norm=False, ax=jg.ax_joint)
        # Hist: hue_order plots in reverse order, so flip hues and mypal
        sns.histplot(x='ice', hue='runs', bins='sturges', common_norm=True,
                    hue_order=rename, palette=mypal, alpha=0.3, pthresh=0.2,
                    element='step', data=df, legend=False, ax=jg.ax_marg_x)
        sns.histplot(y='depth_top', hue='runs', bins='sturges', common_norm=True, pthresh=0.2,
                    hue_order=rename, palette=mypal, alpha=0.3,
                    element='step', data=df, legend=False, ax=jg.ax_marg_y)
        
        # Legend only in 1st subplot
        handles = jg.ax_joint.legend_.get_lines()
        jg.ax_joint.legend_.remove()

        # Gigaton zone
        if i < 2:
            jg.ax_joint.fill_betweenx([10, 1e4], [10, 10], [1e4, 1e4], 
                                       color='tab:gray', alpha=0.5)
            jg.ax_joint.text(40, 11, 'Gigaton\nZone', ha='center', va='top', 
                             fontsize=9)
            
            title = 'Ballistic\nSedimentation'
            leg = jg.ax_joint.legend(handles[::-1], rename, ncol=2, loc="upper left", 
                                    title=title, fontsize=8, title_fontsize=9, 
                                    bbox_to_anchor=(0, 0.91), frameon=False)
            leg.get_title().set_multialignment('center')

        # Cabeus LCROSS depths and legend
        if coldtrap == 'Cabeus':
            jg.ax_joint.axhline(6, ls=(0, (3, 3, 1, 3)), lw=2, color='k', zorder=10, label='Luchsinger et al. (2021)')
            jg.ax_joint.axhline(10, ls='--', color='k', lw=2, zorder=10, label='Schultz et al. (2010)')
            jg.ax_joint.legend(loc='lower right', title=r'LCROSS Penetration Depth', fontsize=8, title_fontsize=8)
        jgs.append(jg)
    
    # Set axis labels
    for i, jg in enumerate(jgs):
        xlabel = 'Ice layer thickness [m]' if i in (4, 5) else None
        ylabel = 'Depth [m]' if (i % 2 == 0) else None
        jg.ax_joint.set_xlabel(xlabel)
        jg.ax_joint.set_ylabel(ylabel)
        jg.ax_joint.set_xscale('log')
        jg.ax_joint.set_yscale('log')
        jg.ax_joint.set_xlim(xlim)
        jg.ax_joint.set_ylim(ylim)
        jg.ax_joint.invert_yaxis()
        jg.ax_joint.set_xticks([0.1, 1, 10, 100])
        jg.ax_marg_x.yaxis.get_major_formatter().set_scientific(False)
        jg.ax_marg_y.xaxis.get_major_formatter().set_scientific(False)
        jg.ax_marg_x.xaxis.set_visible(False)
        jg.ax_marg_y.yaxis.set_visible(False)
    
    # Move all the jointgrids into a single figure using patchwork
    jgs = [pw.load_seaborngrid(jg) for jg in jgs]
    out = (jgs[0] + jgs[1])/(jgs[2] + jgs[3])/(jgs[4] + jgs[5])

    # version = mplt.plot_version(cfg, loc='lr', xyoff=(0.01, -0.15), ax=fig.gca())
    return _save_or_show(out, jgs[0], fsave, figdir, '')#version)   

def ejecta_distance(fsave='ejecta_distance.pdf', figdir=FIGDIR, cfg=CFG):
    """
    Plot ejecta speed, thick, KR, mixing depth as a function of distance.
    
    Oberbeck (1975) Figure 16 shows 4 craters, two < 1 km with no hummocky 
    terrain and larger Mosting C (4.2 km) and Harpalus (41.6 km) have hummocky 
    terrain. Show Ries basin and Meteor crater for comparison.
    """
    mplt.reset_plot_style()
    crater_diams = {
        # "Imbrium": 1.3e6,  # [m]
        # "Crisium": 1.08e6,  # [m]
        "Orientale": 0.94e6,  # [m]
        # "Schrödinger": 326e3,  # [m]
        "Harpalus": 41.6e3,  # [m] Harpalus (Oberbeck d)
        "Ries Basin": 24e3,  # [m]
        "Shackleton": 20.9e3,  # [m] smallest polar
        "Mosting C": 4.2e3,  # [m] Mosting C (Oberbeck c)
        "Meteor Crater": 1e3,  # [m]
        # "Oberbeck b": 0.66e3,  # [m]
        # "crater a": 0.56e3,  # [m]
    }
    # ries_max_obs = 36.5e3  # Max observed dist [m]
    ries_max_d = crater_diams['Ries Basin']*2  # [m] 4 crater radii

    # Configure cfg for terrestrial craters
    earth_dict = cfg.to_dict()
    earth_dict['grav_moon'] = 9.81  # [m/s^2]
    earth_dict['rad_moon'] = 6.371e6  # [m]
    earth_dict['bulk_density'] = 2700  # [kg/m^3]
    earth_cfg = config.Cfg(**earth_dict)

    fig, axs = plt.subplots(2, 2, figsize=(7.2, 6.4), sharex=True, 
                            gridspec_kw={'wspace':0.35, 'hspace':0.02})
    ax1, ax2, ax3, ax4 = axs.flatten()
    colors = plt.rcParams['axes.prop_cycle'].by_key()['color'][:3]
    colors.extend(colors)

    d_crad = np.linspace(1, 5, 100)  # x-axis distance [crater radii]
    for i, (crater, diam) in enumerate(crater_diams.items()):
        ls = '-'
        ccfg = cfg
        plot_mixing_depth = True
        if crater in ('Shackleton', 'Mosting C', 'Meteor Crater'):
            ls = '--'
        if crater in ('Ries Basin', 'Meteor Crater'):  # Terrestrial craters
            ccfg = earth_cfg
            plot_mixing_depth = False
        
        # Compute speed, ke, thickness, mixing depth
        rad = diam / 2  # radius [m]
        dist = rad * d_crad  # distance [m]
        thick = mp.get_ejecta_thickness(dist, rad, ccfg)  # [m]
        vel = mp.ballistic_velocity(dist, ccfg)  # [m/s]
        mass = thick * ccfg.bulk_density  # [kg/m^2]
        ke = mp.kinetic_energy(mass, vel) / 1e6  # [MJ] 
        mr = mp.get_mixing_ratio_oberbeck(diam, ccfg)  # mixing ratio
        depth = thick * mr  # depth [m]
        
        # Plot
        label = f'{crater} (D={diam/1e3:.4g} km)'
        ax1.semilogy(d_crad, vel, ls=ls, c=colors[i], label=label)
        ax2.semilogy(d_crad, thick, ls=ls, c=colors[i], label=label)
        ax3.semilogy(d_crad, ke, ls=ls, c=colors[i], label=label)
        if plot_mixing_depth:
            ax4.semilogy(d_crad, depth, ls=ls, c=colors[i], label=label)
        if crater == 'Ries Basin':
            ries = np.argmin(np.abs(dist - ries_max_d))  # Index of Ries max
            # rvel = vel[ries]
            # ax1.axhline(rvel, ls='--', c='k')
            # ax1.annotate('Bunte Breccia $v_{max}=$'+f'{round(rvel,-1):.0f} m/s', (4, rvel), xytext=(3.82, 2000), ha='center', arrowprops=dict(arrowstyle="->"))
            # rthick = thick[ries]
            # ax2.axhline(rthick, ls='--', c='k')
            # ax2.annotate('Bunte Breccia\n$t_{min}=$'+f'{rthick:.1f} m', (4, rthick), xytext=(5.8, 40), ha='right', arrowprops=dict(arrowstyle="->"))
            rke = round(ke[ries], -2)  # round to 2 sig figs
            ax3.axhline(rke, ls='--', c='k', zorder=5)
            ax3.annotate('Bunte Breccia   \n$KE_{min}=$'+
                         f'{rke:.0f} MJ/m$^2$', (4, rke), ha='right', 
                         xytext=(4.9, 2e5), arrowprops={'arrowstyle': "->"})
        
        if crater == 'Shackleton':
            ax2.fill_between(d_crad, thick, thick_top, color=colors[0], alpha=0.2)
            ax1.fill_between(d_crad, vel, vel_top, color=colors[0], alpha=0.2)
            ax3.fill_between(d_crad, ke, ke_top, color=colors[0], alpha=0.2)
            ax4.fill_between(d_crad, depth, depth_top, color=colors[0], alpha=0.2)
        if crater == 'Orientale':
            thick_top = thick
            vel_top = vel
            ke_top = ke
            depth_top = depth
    # Legend
    h, l = ax1.get_legend_handles_labels()
    newh = [ax1.plot([], marker="", ls="")[0]]*3
    newl = ["This work:", "Oberbeck:", "Terrestrial:"]
    handles = newh + h
    labels = newl + l
    leg = ax1.legend(handles, labels, bbox_to_anchor=(0., 1.02, 2.35, .102), 
                     loc=3, ncol=3, mode="expand", borderaxespad=0.)
    for vpack in leg._legend_handle_box.get_children()[:1]:
        for hpack in vpack.get_children():
            hpack.get_children()[0].set_width(0)

    ax1.set_xlim(1, 5)
    ax1.set_ylim(50, 2e3)
    ax2.set_ylim(None, 3e3)
    ax3.set_ylim(None, 5e6)
    ax4.set_ylim(3e-2, 5e4)
    for ax, letter in zip(axs.flatten(), ('A', 'B', 'C', 'D')):
        ax.annotate(letter, xy=(0.02, 0.98), va='top', fontweight='bold', 
                    fontsize=14, xycoords='axes fraction')

    ax1.set_ylabel('Ejecta velocity, $v$ [$\\rm m/s$]')
    ax2.set_ylabel('Ejecta thickness, $t$ [$\\rm m$]')
    ax3.set_ylabel('Ejecta kinetic energy, KE [$\\rm MJ / m^2$]')
    ax4.set_ylabel('Balistic sedimentation depth, $\delta$ [$\\rm m$]')
    ax3.set_xlabel('Distance [crater radii]')
    ax4.set_xlabel('Distance [crater radii]')
    version = mplt.plot_version(cfg, loc='ur', xyoff=(-0.02, -0.02), ax=ax2)
    return _save_or_show(fig, axs, fsave, figdir, version)


def volatilized_fraction_bsed(fsave='volatilized_fraction_bsed.pdf', figdir=FIGDIR, cfg=CFG, show_avgs=False):
    """
    Plot volatilized fraction as a function of ejecta thickness and ballistic 
    mixing depth.
    """
    mplt.reset_plot_style()
    dm = mp.read_ballistic_melt_frac(True, cfg).copy()  # mean
    ds = mp.read_ballistic_melt_frac(False, cfg).copy()  # std
    # Add 0% melt at T=100 K
    dm.insert(0, 100, 0)  
    ds.insert(0, 100, 0)

    # Get data and axes
    frac_mean = dm.to_numpy()
    frac_std = ds.to_numpy()
    temps = dm.columns.to_numpy()
    mrs = dm.index.to_numpy()
    ejecta_pct = 100*(1 / (1 + mrs))  # target mixing ratio -> ejecta fraction
    extent = [temps.min(), temps.max(), 0, ejecta_pct.max()]

    # Get crater and basin volatilization fractions
    crater_t = cfg.polar_ejecta_temp_init
    basin_tc = cfg.basin_ejecta_temp_init_cold
    basin_tw = cfg.basin_ejecta_temp_init_warm
    df = mp.get_crater_basin_list(cfg)
    dists = mp.get_coldtrap_dists(df, cfg)
    mr = mp.get_mixing_ratio_oberbeck(dists, cfg)
    crater_pct = 100*(1 / (1 + mr[~df.isbasin]))
    basin_pct = 100*(1 / (1 + mr[df.isbasin]))
    crater_pct = crater_pct[~np.isnan(crater_pct)]
    basin_pct = basin_pct[~np.isnan(basin_pct)]
    crater = [[crater_t, crater_t], [crater_pct.min(), crater_pct.max()]]
    basin_c = [[basin_tc, basin_tc], [basin_pct.min(), basin_pct.max()]]
    basin_w = [[basin_tw, basin_tw], [basin_pct.min(), basin_pct.max()]]
    
    # Plot
    fig, axs = plt.subplots(1, 2, figsize=(7.2, 3), sharey=True)
    fig.subplots_adjust(hspace=0.35)    

    ax = axs[0]
    ax.tick_params('x', bottom=False, top=False)
    ax.tick_params('y', direction='out', right=False)
    p = ax.imshow(frac_mean*100, extent=extent, aspect='auto', interpolation='none', cmap='magma')
    ax.plot(*crater, 'o--', ms=4, lw=2, c='tab:cyan', label='Crater')
    ax.plot(*basin_c, 'o--', ms=4, lw=2, c='tab:orange', label='Basin (cold)')
    ax.plot(*basin_w, 'o--', ms=4, lw=2, c='tab:red', label='Basin (warm)')
    ax.set_yticks(range(0, 101, 20))
    ax.set_xticks(range(100, 501, 100))
    ax.legend()
    cbar = fig.colorbar(p, ax=ax)
    cbar.ax.get_yaxis().labelpad = 12
    cbar.ax.set_ylabel("Mean volatilized fraction [%]", rotation=270)
    ax.set_ylabel("Ejecta fraction [%]")
    ax.set_xlabel("Ejecta Temperature [K]")

    ax = axs[1]
    ax.tick_params('x', direction='out', top=False)
    ax.tick_params('y', direction='out', right=False)
    p = ax.imshow(frac_std*100, extent=extent, aspect='auto', interpolation='none', cmap='cividis')
    ax.plot(*crater, 'o--', ms=4, lw=2, c='tab:cyan', label='Crater')
    ax.plot(*basin_c, 'o--', ms=4, lw=2, c='tab:orange', label='Basin (cold)')
    ax.plot(*basin_w, 'o--', ms=4, lw=2, c='tab:red', label='Basin (warm)')
    ax.set_yticks(range(0, 101, 20))
    ax.set_xticks(range(100, 501, 100))
    cbar = fig.colorbar(p, ax=ax)
    cbar.ax.get_yaxis().labelpad = 15
    cbar.ax.set_ylabel("Standard deviation [%]", rotation=270)
    ax.set_xlabel("Ejecta Temperature [K]")

    version = mplt.plot_version(cfg, loc='lr', xyoff=(0.45, -0.22), ax=ax, fontsize=8)
    return _save_or_show(fig, axs, fsave, figdir, version)


def random_crater_ages(fsave='random_crater_ages.pdf', figdir=FIGDIR, cfg=CFG):
    """
    Plot random crater ages.
    """
    mplt.reset_plot_style()
    fig, axs = plt.subplots(2, figsize=(7.2, 9))

    df = mp.read_crater_list(cfg)

    # Get random ages the moonpies way (slow)
    ax = axs[0]
    nseed = 100
    cdict = cfg.to_dict()
    ages = np.zeros((nseed, len(df)))
    bins = np.arange(159.5, 420.5) / 100
    crater_list = list(df.cname)
    for i, seed in enumerate(range(nseed)):
        cdict['seed'] = seed
        cfg = config.Cfg(**cdict)
        rng = mp.get_rng(cfg)
        df = mp.read_crater_list(cfg)
        df_rand = mp.randomize_crater_ages(df, cfg.timestep, rng).set_index('cname')
        ages[i] = df_rand.loc[crater_list, 'age'] / 1e9

    for i in range(ages.shape[1]):
        if i < 11:
            ls = 'solid'
        elif i < 22:
            ls = 'dashed'
        else:
            ls = 'dotted'
        ax.hist(ages[:, i], bins=bins, label=crater_list[i], histtype='step', ls=ls)
    ax.legend(ncol=4, fontsize=8)
    ax.set_xlim(4.22, ages.min())
    ax.set_ylabel('Count [runs]')
    ax.set_title(f'Random crater ages ({nseed} samples)')

    # Get random ages the scipy way (fast)
    ax = axs[1]
    left, bottom, width, height = [0.65, 0.55, 0.3, 0.3]
    axb = ax.inset_axes([left, bottom, width, height])
    
    nseed = int(1e5)
    sig = df[['age_low', 'age_upp']].mean(axis=1)/2
    a = df.age_low
    b = df.age_upp
    rng = mp.get_rng(cfg)
    S = stats.truncnorm.rvs(-a/sig, b/sig, df.age, sig, (nseed, len(df)), random_state=rng)
    S = mp.round_to_ts(S, cfg.timestep) / 1e9
    bins = np.arange(159.5, 420.5) / 100
    for i in range(S.shape[1]):
        Srow = S[:, i]
        ax.hist(Srow, bins=bins, histtype='step')
        Syoung = Srow < 3
        if Syoung.any():
            axb.hist(Srow[Syoung], bins=bins, histtype='step')

    ax.set_title(f'Random crater ages ({nseed} samples)')
    ax.set_xlabel('Age [Ga]')
    axb.set_xlabel('Age [Ga]')
    ax.set_xlim(4.22, 2.89)
    axb.set_xlim(2.2, 1.6)
    ax.set_ylabel('Count [runs]')
    version = mplt.plot_version(cfg, loc='lr', xyoff=(0.01, -0.17), ax=axs[1])
    return _save_or_show(fig, axs, fsave, figdir, version)


def strat_cols_bsed(fsave='strat_cols_bsed.pdf', figdir=FIGDIR, cfg=CFG,
                    datedir=DATEDIR, runs=('moonpies', 'no_bsed'), seed=7,
                    min_thick=5, corder=CORDER, fsave_icepct=''):
    """
    Plot stratigraphy columns comparing bsed and no bsed.
    """
    mplt.reset_plot_style()
    if not datedir:
        datedir = Path(cfg.out_path).parents[1]
    fig = mplt.plot_stratigraphy(datedir, corder, runs, [seed], min_thick, 
                                 version=False, fsave_icepct=fsave_icepct)
    ax = fig.axes[-1]
    version = mplt.plot_version(cfg, loc='lr', xyoff=(0.01, -0.2), ax=ax)

    # Find coords for subplot annotations (top left of row 1 and 2)
    axa = fig.axes[1]
    axb = next(ax for ax in fig.axes[2:] 
               if ax.get_window_extent().get_points()[0, 1] 
               != axa.get_window_extent().get_points()[0, 1])
    kw = dict(va='top', fontweight='bold', fontsize=20, xycoords='axes fraction')
    axa.annotate('A', xy=(-0.5, 1), **kw)  # 0.052, 0.9
    axb.annotate('B', xy=(-0.5, 1), **kw)  # 0.052, 0.5
    return _save_or_show(fig, ax, fsave, figdir, version)


def strat_cols_seeds(fsave='strat_cols_seeds.pdf', figdir=FIGDIR, cfg=CFG,
                     datedir=DATEDIR, runs=('moonpies',), seeds=(13, 8, 1),
                     min_thick=5, corder=('Faustini', 'Haworth', 'Cabeus'),
                     fsave_icepct=''):
    """
    Plot stratigraphy columns comparing bsed and no bsed.
    """
    mplt.reset_plot_style()
    if not datedir:
        datedir = Path(cfg.out_path).parents[1]
    fig = mplt.plot_stratigraphy(datedir, corder, runs, seeds, min_thick, 
                                 version=False, fsave_icepct=fsave_icepct)
    ax = fig.axes[-1]
    version = mplt.plot_version(cfg, loc='lr', xyoff=(0.01, -0.2), ax=ax)

    # Find coords for subplot annotations (top left of row 1 and 2)
    axa = fig.axes[1]
    axb = fig.axes[5]
    axc = fig.axes[9]
    kw = dict(va='top', fontweight='bold', fontsize=20, xycoords='axes fraction')
    axa.annotate('A', xy=(-0.5, 1), **kw)
    axb.annotate('B', xy=(-0.5, 1), **kw)
    axc.annotate('C', xy=(-0.5, 1), **kw)
    return _save_or_show(fig, ax, fsave, figdir, version)


def surface_boxplot(fsave='surface_boxplot.pdf', figdir=FIGDIR, cfg=CFG, 
                    datedir=DATEDIR, corder=CORDER, sdepths=[6, 100], verbose=False):
    """
    Plot surface boxplot.
    """
    mplt.reset_plot_style()
    _, runs, nruns = _load_aggregated(cfg, datedir, flatten=True, nruns=True)
    runs = runs[runs.runs == 'moonpies']
      
    fig, axs = plt.subplots(len(sdepths), figsize=(7.2, 4.5*len(sdepths)))
    axs = [axs] if len(sdepths) == 1 else axs
    for i, sdepth in enumerate(sdepths):
        key = f'total ice {sdepth}m'
        ax = axs[i]
        ax = sns.boxplot(x='coldtrap', y=key, data=runs, 
                        order=corder, fliersize=1, whis=(1, 95), ax=ax)
        ax.set_xlabel('')
        ax.set_ylabel(f'Total ice thickness [m] (upper {sdepth} m, {nruns/1e3:.3g}k runs)')
        ax.set_ylim(0, sdepth/3)
        ax.set_xticklabels(ax.get_xticklabels(), rotation=30)

        # 5% line
        ax.axhline(sdepth*0.05, color='k', linestyle='--', linewidth=1)
        ax.annotate('5%', xy=(len(corder)-1, sdepth*0.052))
        # Annotate
        if sdepth == 6:
            ax.set_ylim(0, 1)
            pct75 = runs[runs.coldtrap=='Faustini'][key].quantile(0.75)
            pct99 = runs[runs.coldtrap=='Faustini'][key].quantile(0.95)
            ax.annotate('p75', xy=(0.2, pct75), xytext=(0.3, pct75+0.1), 
                        fontstyle='italic', arrowprops=dict(facecolor='black', 
                        headlength=6, headwidth=6, width=1, shrink=0.02))
            ax.annotate('p99', xy=(0.2, pct99), xytext=(0.3, pct99+0.1), 
                        fontstyle='italic', arrowprops=dict(facecolor='black', 
                        headlength=6, headwidth=6, width=1, shrink=0.02))

        # Verbose
        thresh = 0.3 if sdepth == 6 else 5 # m
        if verbose:
            print('\nSdepth:', sdepth, 'm')
        for coldtrap in runs.coldtrap.unique():
            gt_thresh = runs[runs.coldtrap == coldtrap][key] > thresh
            gt_frac = gt_thresh.sum() / len(gt_thresh)
            if verbose:
                print(f'{coldtrap} exceeds {thresh:.2g} m {gt_frac:.2%} of the time')
    version = mplt.plot_version(cfg, loc='ur', ax=axs[0])
    return _save_or_show(fig, ax, fsave, figdir, version)


def plot_by_module(fsave='plot_by_module.pdf', figdir=FIGDIR, cfg=CFG, 
                   seeds=range(10)):
    """Plot ice delivery and loss by module."""
    mplt.reset_plot_style()

    era_labels = ['Pre-Nec.', 'Nec.', 'Imb.', 'Era.', 'Cop.']
    era_ages = [4.26, 3.97, 3.83, 3.2, 1.1, 0]  # Age bins
    colors = ("#0072B2", "#E69F00", "#009E73", "#D55E00", "#F0E442", "#CC79A7")
    mpl.rcParams.update({
        'font.size': 12,
        'axes.grid': False,
        'xtick.top': False,
        'xtick.bottom': False,
        'axes.prop_cycle': mpl.cycler(color=colors) 
    })
    order = ['Total ice', 'Impactor ice', 'Basin ice', 'Volcanic ice', 
            'Solar wind ice', 'Gardening depth', 'Ballistic sed depth']
    impactor_keys = ['Micrometeorite ice',
        'Small impactor ice', 'Small simple crater ice',
        'Large simple crater ice', 'Large complex crater ice']
    other_ice_keys = ['Volcanic ice', 'Solar wind ice', 'Basin ice']
    loss_keys = ['Gardening depth', 'Ballistic sed depth']

    df = _get_ice_ast_comet_seeds(cfg, seeds, loss_keys).reset_index()

    df['Impactor ice'] = np.sum(df[impactor_keys], axis=1)
    df['Total ice'] = np.sum(df[impactor_keys + other_ice_keys], axis=1)
    time = df['time']
    tmp = df.drop(impactor_keys + ['time'], axis=1)
    tmp = tmp[order]

    # Groupby era. Need to flip to ascending time order then reindex after
    bins = np.array(era_ages[::-1])*1e9
    binlabels = era_labels[::-1]
    icegb = tmp.groupby(pd.cut(time, bins=bins, labels=binlabels))
    df_mean = icegb.agg('mean').reindex(era_labels)
    df_min = icegb.agg('min').reindex(era_labels)
    df_max = icegb.agg('max').reindex(era_labels)

    # Init plot
    n = len(df_mean)
    fig, ax = plt.subplots(figsize=(7.5, 4))
    ax.set_yscale('log')
    ax.set_ylim(1e-4, 1e2)
    ax.set_xlim(-0.5, 4.5)
    ax.tick_params(axis='both')
    ax.set_xticks(np.arange(n))
    ax.set_xticklabels(list(df_mean.index))
    ax.set_ylabel('Ice deposited per km$^2$ per timestep [m]')

    
    width = 1/n
    x = np.arange(n+1) - 0.5
    _ = [ax.axvline(era, color='k', lw=1) for era in x]  # Diviners
    x = np.repeat(x, 2)[1:-1]

    # Shade loss processes
    for label, c, a, h in zip((loss_keys), ('gray', 'red'), (0.3, 0.2), ('\\', '')):
        y = df_mean[label].values
        y = np.repeat(y, 2)
        ax.fill_between(x, [0]*len(y), y, color=c, alpha=a, label='Max ' + label, hatch=h)

    # Bar charts of ice by era
    for i, (label, col) in enumerate(df_mean.items()):
        if label in loss_keys:
            continue
        x = np.arange(n) - width*(n-1)/2 + (i*width)
        yerr = [col-df_min.iloc[:,i], df_max.iloc[:,i]-col]
        yerr[0] = yerr[0].clip(lower=1e-9)  # Prevent negative error bars
        ax.bar(x, col, label=label, width=width, yerr=yerr, capsize=4)

    # Legend (customize order)
    handles, labels = plt.gca().get_legend_handles_labels()
    order = [2, 3, 4, 5, 6, 1, 0]
    ax.legend([handles[i] for i in order], [labels[i] for i in order], ncol=2, 
                loc='upper right', fontsize=8, framealpha=1)
    
    version = mplt.plot_version(cfg, loc='ul', fontsize=8)
    return _save_or_show(fig, ax, fsave, figdir, version)


# Plot by module helpers
def _get_ice_ast_comet_seeds(cfg, seeds, loss_keys):
    """Return DataFrame of ice by module at each time step avg over seeds."""
    # Get ice by module
    cdict = cfg.to_dict()
    time_arr = mp.get_time_array(cfg)
    df = mp.get_crater_basin_list(cfg)
    adf = _get_ice_by_module(df, time_arr, cfg, 0) * 0
    cdf = adf.copy()

    # Avg across seeds
    for i, seed in enumerate(seeds):
        cdict['seed'] = seed
        cfg = config.Cfg(**cdict)

        mp.clear_cache()
        rng = mp.get_rng(cfg)
        df = mp.get_crater_basin_list(cfg, rng)
        adf += _get_ice_by_module(df, time_arr, cfg, rng)

        mp.clear_cache()
        comet_cfg = mp.get_comet_cfg(cfg)
        rng = mp.get_rng(comet_cfg)
        df = mp.get_crater_basin_list(comet_cfg, rng)
        cdf += _get_ice_by_module(df, time_arr, comet_cfg, rng)

    adf /= len(seeds)
    cdf /= len(seeds)
    # Total ast and comet ice (frac already accounted for in cfg)
    df = adf.set_index('time') + cdf.set_index('time')
    df = df.drop(loss_keys, axis=1)
    for k in loss_keys:
        # Should be same for ast and comet but avg just in case
        df[k] = (adf[k] + cdf[k]).values / 2
    return df

def _get_ice_by_module(df, time_arr, cfg, rng):
    """Return DataFrame with ice by module at each time step."""
    out = pd.DataFrame(time_arr, columns=['time'])
    out['Volcanic ice'] = mp.get_volcanic_ice(time_arr, cfg)
    out['Solar wind ice'] = mp.get_solar_wind_ice(time_arr, cfg)
    out['Micrometeorite ice'] = mp.get_micrometeorite_ice(time_arr, cfg)
    out['Small impactor ice'] = mp.get_small_impactor_ice(time_arr, cfg)
    out['Small simple crater ice'] = mp.get_small_simple_crater_ice(time_arr, cfg)
    out['Large simple crater ice'] = mp.get_large_simple_crater_ice(time_arr, cfg, rng)
    out['Large complex crater ice'] = mp.get_complex_crater_ice(time_arr, cfg, rng)
    out['Basin ice'] = mp.get_basin_ice(time_arr, df, cfg, rng)
    out['Gardening depth'] = mp.overturn_depth_time(time_arr, cfg)
    out['Ballistic sed depth'] = _get_agg_bsed_depth(df, time_arr, cfg, rng)
    return out


def _get_agg_bsed_depth(df, time_arr, cfg, rng, agg=np.mean):
    """Return average ballistic sedimentation depth at each time step."""
    ej_dists = mp.get_coldtrap_dists(df, cfg)
    bsed_d, bsed_frac = mp.get_bsed_depth(time_arr, df, ej_dists, cfg)
    bsed_all = bsed_d * bsed_frac
    return np.apply_along_axis(agg, 1, bsed_all)


# Supplementary Information Figures
def ballistic_hop(fsave='bhop_lat.png', figdir=FIGDIR, cfg=CFG):
    """
    Plot ballistic hop efficiency by latitude.

    :Authors:
        K. M. Luchsinger, C. J. Tai Udovicic
    """
    mplt.reset_plot_style()
    coldtraps = ['Haworth', 'Shoemaker', 'Faustini', 'Amundsen', 'Cabeus',
                 'Cabeus B', 'de Gerlache', "Idel'son L", 'Sverdrup', 
                 'Shackleton', 'Wiechert J', "Slater"]
    lats = np.array([87.5, 88., 87.1, 84.4, 85.3, 82.3, 88.3, 84., 88.3, 
                     89.6, 85.2, 88.1])
    label_offset = np.array([(-0.7, 0.1), (-0.9, -0.6), (-0.5, 0.2), (-0.3, -0.7), (-0.1, -0.7), (-0.2, -0.7), (0.1, 0.2), 
                            (-0.5, 0.2), (-0.1, -0.8), (-0.95, -0.45), (-0.7, 0.2), (-0.45, 0.1)])
    coldtraps_moores = ["Haworth", "Shoemaker", "Faustini", "de Gerlache", 
                        "Sverdrup", "Shackleton", "Cabeus"]

    fig, ax = plt.subplots(figsize=(8,4))
    ax.grid(True)
    # Plot cold trap bhop vs. lat
    bhops = mp.read_ballistic_hop_csv(cfg.bhop_csv_in)
    for i, (name, lat) in enumerate(zip(coldtraps, lats)):
        bhop = 100*bhops.loc[name]
        color = 'tab:orange'
        marker = 's'
        kw = dict(markerfacecolor='white', markeredgewidth=2, zorder=10)
        label = None
        if name in coldtraps_moores:
            color = 'tab:blue'
            marker = 'o'
            kw = {}
        if name == 'Haworth':
            label = 'Moores et al. (2016)'
        elif name == 'Cabeus B':
            label = 'This work'
            
        ax.plot(lat, bhop, marker, c=color, label=label, **kw)
        off_x, off_y = label_offset[i]
        ax.annotate(name, (lat, bhop), xytext=(lat + off_x, bhop+off_y), ha='left', va='bottom')
    
    # Cannon et al. (2020) constant bhop
    ax.axhline(5.4, c='tab:gray', ls='--')
    ax.annotate('Cannon et al. (2020)', (90, 5.3), ha='right', va='top')


    # Simple linear fit to moores data
    bhop_moores = [100*bhops.loc[name] for name in coldtraps if name in coldtraps_moores]
    lats_moores = [lat for name, lat in zip(coldtraps, lats) if name in coldtraps_moores]
    fit = np.poly1d(np.squeeze(np.polyfit(lats_moores, bhop_moores, 1)))
    lat = np.linspace(89.6, 85.6, 10)
    ax.plot(lat, fit(lat), '--')
    ax.annotate("Fit to Moores et al. (2016)", (86.6, fit(86.6)), va='top', ha='right')

    # Line from Cabeus B to Faustini
    bhop_cf = 100*bhops.loc[['Cabeus B', 'Faustini']].values
    ax.plot([82.3, 87.1], bhop_cf, '--', c='tab:orange')

    ax.set_xlim(82, 90)
    ax.set_ylim(0, 7)
    ax.set_xlabel("Latitude [Degrees]")
    ax.set_ylabel("Ballistic Hop Efficiency [% per km$^{2}$]")
    # ax.set_title("Ballistic Hop Efficiency by Latitude")
    ax.legend()
    version = mplt.plot_version(cfg, loc='ll', ax=ax)
    fig.tight_layout()
    return _save_or_show(fig, ax, fsave, figdir, version)


def ast_comet_vels(fsave='comet_vels.png', figdir=FIGDIR, cfg=CFG):
    """
    Plot comet velocity distributions.

    :Authors:
        K. M. Luchsinger, C. J. Tai Udovicic
    """
    mplt.reset_plot_style()
    rng = mp.get_rng(cfg)
    cfg_comet = mp.get_comet_cfg(cfg)
    n = int(1e5)
    
    # Get probability distributions and random samples
    rv_ast = mp.asteroid_speed_rv(cfg)
    rv_comet = mp.comet_speed_rv(cfg_comet)

    x = np.linspace(0, cfg.comet_speed_max, int(1e4))
    apdf = rv_ast.pdf(x)
    cpdf = rv_comet.pdf(x)
    aspeeds = mp.get_random_impactor_speeds(n, cfg, rng)
    cspeeds = mp.get_random_impactor_speeds(n, cfg_comet, rng)

    fig, axs = plt.subplots(2, sharex=True, figsize=(7, 5))
    # Plot asteroid and comet distributions
    ax = axs[0]
    ax.plot(x, apdf, '-.', c='tab:blue', lw=2, label='Asteroid pdf')
    ax.plot(x, cpdf, '-.', c='tab:orange', lw=2, label='Comet pdf')
    bins = np.linspace(0, cfg.comet_speed_max, 40)
    ax.hist(aspeeds, bins, histtype='stepfilled', density=True,
            color='tab:blue', alpha=0.2, label='Asteroid Random sample')
    ax.hist(cspeeds, bins, histtype='stepfilled', density=True,
            color='tab:orange', alpha=0.2, label='Comet Random sample')
    ax.set_xlim(0, 80000)
    ax.set_ylabel('Density')
    ax.legend(loc='center right')

    # Plot comet mixed probability distribution
    ax = axs[1]
    ax.set_ylabel('Probability')
    ax.plot(x, rv_comet.sf(x), label='Survival function (SF)')
    ax.plot(x, rv_comet.cdf(x), label='CDF')
    ax.set_ylim(0, 1)

    ax2 = ax.twinx()
    ax2.set_ylabel('Density')
    ax2.plot(x, rv_comet.pdf(x), '-.', c='tab:green', label='PDF')
    ax2.hist(cspeeds, bins=40, density=True, color='tab:gray', alpha=0.5, 
            zorder=0, label=f'Samples (n={n:.0e})')

    lines, labels = ax.get_legend_handles_labels()
    lines2, labels2 = ax2.get_legend_handles_labels()
    ax.legend(lines + lines2, labels + labels2, title='Comet distribution', 
              loc='center right')
    ax.set_xticks(ax.get_xticks())  # Neeed for setting labels
    ax.set_xticklabels(ax.get_xticks()/1e3)  # [m/s] -> [km/s]
    ax.set_xlabel('Speed [km/s]')
    ax.set_xlim(0, cfg.comet_speed_max)

    version = mplt.plot_version(cfg, loc='ur', ax=axs[0])
    return _save_or_show(fig, axs, fsave, figdir, version)


def ice_retention(fsave='ice_retention.png', figdir=FIGDIR):
    """Plot ice retention as a function of impactor speed."""
    mplt.reset_plot_style()

    # Set config
    cfg_c = config.Cfg(mode='cannon')
    cfg_m_asteroid = config.Cfg(mode='moonpies')
    cfg_m_comet = config.Cfg(mode='moonpies', is_comet=True)

    # Data from Ong et al. (2010)
    ong_x = [10, 15, 30, 45, 60]
    ong_y = [1, 1.97E-01, 1.47E-02, 1.93E-03, 6.60E-06]

    # Generate moonpies data
    v = np.linspace(0, 70, 7000)  # speed [km/s]
    retention_c = mp.ice_retention_factor(v*1e3, cfg_c)
    retention_ma = mp.ice_retention_factor(v*1e3, cfg_m_asteroid)
    retention_mc = mp.ice_retention_factor(v*1e3, cfg_m_comet)

    # Make plot
    fig, ax = plt.subplots(figsize=(7, 3.5))
    ax.semilogy(v, retention_c, c='tab:gray', lw=3, label='Cannon et al. (2020)')
    ax.semilogy(v, retention_ma, ':', c='k', lw=2, label='This work, asteroid')
    ax.semilogy(v, retention_mc, '--', c='tab:blue', lw=2, label='This work, comet')
    ax.plot(ong_x, ong_y, 'o', ms=8, c='k', label='Ong et al. (2010)')
    ax.set_title('Ice Retention vs Impact Speed')
    ax.set_ylabel('Ice Retention Fraction [0-1]')
    ax.set_xlabel('Impact Speed [km/s]')
    ax.set_ylim(1E-6, 1.5)
    ax.set_xlim(0, 65)
    ax.legend()
    ax.grid(True, which='major', alpha=0.5)

    # Add version and save figure
    mplt.plot_version(cfg_c, loc='ll')
    return _save_or_show(fig, ax, fsave, figdir)


def basin_ice(fsave='basin_ice.png', figdir=FIGDIR, cfg=CFG, n=500):
    """
    Plot basin ice volume by latitude.

    :Authors:
        K. R. Frizzell, C. J. Tai Udovicic
    """
    def moving_avg(x, w):
        """Return moving average of x with window size w."""
        return np.convolve(x, np.ones(w), 'same') / w
    mplt.reset_plot_style()
    # Params
    seed0 = 200  # Starting seed
    window = 3  # Window size for moving average
    color = {'Asteroid': 'tab:gray', 'Comet': 'tab:blue'}
    marker = {'Asteroid': 'x', 'Comet': '+'}

    time_arr = mp.get_time_array()
    fig, ax = plt.subplots()
    for btype in ('Asteroid', 'Comet'):
        all_basin_ice = np.zeros([len(time_arr), n])
        cdict = cfg.to_dict()
        for i, seed in enumerate(range(seed0, seed0+n)):
            mp.clear_cache()
            cdict['seed'] = seed
            cfg = config.Cfg(**cdict)
            df = mp.get_crater_basin_list(cfg)
            if btype == 'Comet':
                cfg = mp.get_comet_cfg(cfg)
            b_ice_t = mp.get_basin_ice(time_arr, df, cfg)
            all_basin_ice[:, i] = b_ice_t
        x = time_arr / 1e9
        ax.semilogy(x, all_basin_ice, marker[btype], c=color[btype], alpha=0.5)
        # median = moving_avg(np.median(all_basin_ice,axis=1), window)
        mean = moving_avg(np.mean(all_basin_ice,axis=1), window)
        pct99 = moving_avg(np.percentile(all_basin_ice, 99.7, axis=1), window)
        ax.plot(x, mean, '-', c=color[btype], lw=2, label=btype+' mean')
        ax.plot(x, pct99,'--', c=color[btype], alpha=0.5, lw=2, label='99.7 percentile')
    ax.grid('on')
    ax.set_xlim(4.25, 3.79)
    ax.set_ylim(0.1, None)
    ax.set_title(f'Ice Delivered to South Pole by Basins ({n} runs)')
    ax.set_xlabel('Time [Ga]')
    ax.set_ylabel('Total ice thickness [m]')
    ax.legend(loc='upper right', ncol=2)
    version = mplt.plot_version(cfg, loc='ul', ax=ax)
    return _save_or_show(fig, ax, fsave, figdir, version)


def bsed_sensitivity_violin(datedir=DATEDIR):
    """Plot ballistic sedimentation sensitivity violin plots."""
    return compare_violin('bsed50_violin.png', datedir=datedir,
                          run_names=('bsed_50pct','no_bsed'), 
                          rename=('50% lost', '0% lost'), 
                          title='Ballistic Sedimentation\nLoss Fraction ')


def comet_sensitivity_violin(datedir=DATEDIR):
    """Plot comet sensitivity violin plots."""
    return compare_violin('comet_violin.png', datedir=datedir,
                          run_names=('moonpies', 'comet_100pct'), 
                          rename=('20%', '100%'), 
                          title='Comet Hydration [wt%]\n')

def ice_pct_fig7(datedir=DATEDIR):
    """Plot ice percentage of each layer in figure 7."""
    _ = strat_cols_seeds(False, datedir=datedir, fsave_icepct='./strat_cols_f7.csv')
    df = pd.read_csv('./strat_cols_f7.csv', header=[0, 1, 2])
    return (df.round(2).style
            .format('{:.3g}%', na_rep='')
            .background_gradient(cmap='Blues', vmin=0, vmax=10, axis=None)
    )
 
def ice_pct_fig8(datedir=DATEDIR):
    """Plot ice percentage of each layer in figure 8."""
    _ = strat_cols_bsed(False, datedir=datedir, fsave_icepct='./strat_cols_f8.csv')
    df = pd.read_csv('./strat_cols_f8.csv', header=[0, 1, 2])
    top = (df['moonpies']['7'].round(2).style
           .format('{:.3g}%', na_rep='')
           .background_gradient(cmap='Blues', vmin=0, vmax=10, axis=None))
    bot = (df['no_bsed']['7'].round(2).style
           .format('{:.3g}%', na_rep='')
           .background_gradient(cmap='Blues', vmin=0, vmax=10, axis=None))
    return top, bot


def grid_plots(fsave='grid_plots.png', figdir=FIGDIR, cfg=CFG):
    """
    Plot gridded computations:
    - most recent surface age (including ejecta)
    - cumulative ejecta, no excavation no self-deposition.
    
    """
    mplt.reset_plot_style()
    
    @mpl.ticker.FuncFormatter
    def km_formatter(x, pos):
        return f'{x/1000:.0f}'

    # Compute cumulative ejecta
    df = mp.get_crater_basin_list(cfg)
    grdy, grdx = mp.get_grid_arrays(cfg)
    age, ejthick = mp.get_grid_outputs(df, grdx, grdy)
    age = age / 1e9  # [yr] -> [Gyr]
    cumu_ej = np.nansum(ejthick, axis=0)
    
    # Plot
    fig, axs = plt.subplots(2, figsize=(6, 11))
    # Age
    ax = axs[0]
    p = ax.pcolor(grdx, grdy, age, vmin=1, vmax=4.25, cmap='viridis', shading='auto')
    cbar = fig.colorbar(p)
    cbar.set_label('Age [Gyr]', rotation=270, labelpad=10)

    # Ejecta thickness
    ax = axs[1]
    p = ax.pcolor(grdx, grdy, cumu_ej, cmap='viridis', shading='auto',
                  norm=mpl.colors.LogNorm(vmin=10, vmax=2000))
    cbar = fig.colorbar(p)
    cbar.set_label('Cumulative Ejecta Thickness [m]', rotation=270, labelpad=10)
    
    for ax in axs:
        # South pole marker
        ax.plot([0], [0], 'k*', ms=5, label='South pole')
        ax.legend()
        ax.xaxis.set_major_formatter(km_formatter)
        ax.yaxis.set_major_formatter(km_formatter)
        ax.set_xlabel('X [km]')
        ax.set_ylabel('Y [km]')

    version = mplt.plot_version(cfg, loc='ll', ax=ax)
    return _save_or_show(fig, ax, fsave, figdir, version)


def plot_by_module_time(fsave='plot_by_module_time.png', figdir=FIGDIR, 
                        cfg=CFG, seeds=range(10), bins=85):
    """Plot ice delivery and loss by module."""
    mplt.reset_plot_style()
    loss_keys = ['Gardening depth', 'Ballistic sed depth']

    df = _get_ice_ast_comet_seeds(cfg, seeds, loss_keys).reset_index()
    grp = df.groupby(pd.cut(df['time'], bins=85)).agg('mean').set_index('time')
    cumu = df.set_index('time').cumsum()

    fig, axs = plt.subplots(1, 2, figsize=(8.5, 3.5))
    fig.subplots_adjust(wspace=0.35)

    # Shade loss processes
    for ax, data in zip(axs, (grp, cumu)):
        x = np.repeat(data.index.values, 2)
        for label, c, a, h in zip((loss_keys), ('gray', 'red'), (0.2, 0.1), ('\\', '')):
            y = np.repeat(data[label].values, 2)
            ax.fill_between(x, [1e-9]*len(y), y, color=c, alpha=a, label='Max ' + label, hatch=h)
        data = data.drop(loss_keys, axis=1)
        legend = ax == axs[0]
        data.plot(logy=True, ax=ax, legend=legend)

    axs[0].set_ylabel('Ice deposited per km$^2$ per timestep [m]')
    axs[1].set_ylabel('Cumulative ice deposited per km$^2$ [m]')
    for ax in axs:
        ax.set_xlabel('Time [yr]')
        ax.set_xlim(4.25e9, 0)
    axs[0].set_ylim(1e-7, 3e2)
    axs[1].set_ylim(1e-3, 1e3)

    # Legend
    handles, labels = plt.gca().get_legend_handles_labels()
    order = list(range(2, len(handles))) + [1, 0]
    axs[0].legend([handles[i] for i in order], [labels[i] for i in order], 
                  bbox_to_anchor=(0., 1.02, 2.35, .102), 
                  loc=3, ncol=3, mode="expand", borderaxespad=0)
    version = mplt.plot_version(cfg, loc='ur', fontsize=8, ax=axs[0])
    return _save_or_show(fig, ax, fsave, figdir, version)


if __name__ == '__main__':
    _generate_all()
