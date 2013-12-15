"""
Functions to load supported file formats into a Data() object.

These are high-level helper functions that just pack the data in a Data()
object. The low-level format decoding functions are in dataload folder.
"""

import cPickle as pickle
from dataload.multi_ch_reader import load_data_ordered16
from dataload.smreader import load_sm


##
# Multi-spot loader functions
#
def load_multispot8(fname, bytes_to_read=-1, swap_D_A=True, BT=0, gamma=1.):
    """Load a 8-ch multispot file and return a Data() object. Cached version.
    """
    fname_c = fname + '_cache.pickle'
    try:
        var = pickle.load(open(fname_c, 'rb'))
        dx = Data(fname=fname, clk_p=12.5e-9, nch=8, BT=BT, gamma=gamma)
        dx.add(ph_times_m=var['ph_times_m'], A_em=var['A_em'], ALEX=False)
        pprint(" - File loaded from cache: %s\n" % fname)
    except IOError:
        dx = load_multispot8_core(fname, bytes_to_read=bytes_to_read,
                                  swap_D_A=swap_D_A, BT=BT, gamma=gamma)
        D = {'ph_times_m': dx.ph_times_m, 'A_em': dx.A_em}
        pprint(" - Pickling data ... ")
        pickle.dump(D, open(fname_c, 'wb'), -1)
        pprint("DONE\n")
    return dx

def load_multispot8_core(fname, bytes_to_read=-1, swap_D_A=True, BT=0,
                         gamma=1.):
    """Load a 8-ch multispot file and return a Data() object.
    """
    dx = Data(fname=fname, clk_p=12.5e-9, nch=8, BT=BT, gamma=gamma)
    ph_times_m, A_em, ph_times_det = load_data_ordered16(fname=fname,
            n_bytes_to_read=bytes_to_read, swap_D_A=swap_D_A)
    dx.add(ph_times_m=ph_times_m, A_em=A_em, ALEX=False)
    return dx

##
# usALEX loader functions
#

# Build masks for the alternating periods
def _select_outer_range(times, period, edges):
    return ((times % period) > edges[0]) + ((times % period) < edges[1])

def _select_inner_range(times, period, edges):
    return ((times % period) > edges[0]) * ((times % period) < edges[1])
    
def _select_range(times, period, edges):
    return _select_inner_range(times, period, edges) if edges[0] < edges[1] \
            else _select_outer_range(times, period, edges)

def load_usalex(fname, BT=0, gamma=1., header=166, bytes_to_read=-1):
    """Load a usALEX file and return a Data() object.
    
    To load usALEX data follow this pattern:
    
        d = load_usalex(fname=fname, BT=0, gamma=1.)
        d.add(D_ON=(2850, 580), A_ON=(900, 2580), alex_period=4000)
        plot_alternation_hist(d)
    
    If the plot looks good apply the alternation with:
    
        usalex_apply_period(d)
    """             
    print " - Loading '%s' ... " % fname
    ph_times_t, det_t = load_sm(fname, header=header) 
    print " [DONE]\n"
    
    DONOR_ON = (2850, 580)
    ACCEPT_ON = (930, 2580)
    alex_period = 4000

    dx = Data(fname=fname, clk_p=12.5e-9, nch=1, BT=BT, gamma=gamma, 
              ALEX=True,
              D_ON=DONOR_ON, A_ON=ACCEPT_ON, alex_period=alex_period,
              ph_times_t=ph_times_t, det_t=det_t, det_donor_accept=(0, 1),
              )
    return dx

def usalex_apply_period(d, delete_ph_t=True):
    """Applies the alternation period previously set.
    
    To load usALEX data follow this pattern:
    
        d = load_usalex(fname=fname, BT=0, gamma=1.)
        d.add(D_ON=(2850, 580), A_ON=(900, 2580), alex_period=4000)
        plot_alternation_hist(d)
    
    If the plot looks good apply the alternation with:
    
        usalex_apply_period(d)
    """
    donor_ch, accept_ch  = d.det_donor_accept
    # Remove eventual ch different from donor or acceptor    
    d_ch_mask_t = (d.det_t == donor_ch)
    a_ch_mask_t = (d.det_t == accept_ch)
    valid_mask = d_ch_mask_t + a_ch_mask_t
    ph_times_val = d.ph_times_t[valid_mask]
    d_ch_mask_val = d_ch_mask_t[valid_mask]
    a_ch_mask_val = a_ch_mask_t[valid_mask]
    assert (d_ch_mask_val + a_ch_mask_val).all()
    assert not (d_ch_mask_val * a_ch_mask_val).any()
    
    print "#donor: %d  #acceptor: %d \n" % (d_ch_mask_val.sum(), 
                                            a_ch_mask_val.sum())

    # Build masks for excitation windows
    d_ex_mask_val = _select_range(ph_times_val, d.alex_period, d.D_ON)
    a_ex_mask_val = _select_range(ph_times_val, d.alex_period, d.A_ON)
    # Safety check: each ph is either D or A ex (not both)
    assert not (d_ex_mask_val * a_ex_mask_val).any()
    
    mask = d_ex_mask_val + a_ex_mask_val  # Removes alternation transients
    
    # Assign the new ph selection mask
    ph_times = ph_times_val[mask]
    d_em = d_ch_mask_val[mask]
    a_em = a_ch_mask_val[mask]
    d_ex = d_ex_mask_val[mask]
    a_ex = a_ex_mask_val[mask]
    
    assert d_em.sum() + a_em.sum() == ph_times.size
    assert (d_em * a_em).any() == False
    assert a_ex.size == a_em.size == d_ex.size == d_em.size == ph_times.size
    
    d.add(ph_times_m=[ph_times],
          D_em=[d_em], A_em=[a_em], D_ex=[d_ex], A_ex=[a_ex],)
          
    assert d.ph_times_m[0].size == d.A_em[0].size
    
    if delete_ph_t:
        d.delete('ph_times_t')
        d.delete('det_t')
    return d
              

