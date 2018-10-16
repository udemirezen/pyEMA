import numpy as np
import matplotlib.pyplot as plt
import time
import scipy.linalg
from tqdm import tqdm_notebook as tqdm
from scipy.linalg import toeplitz

class lscf():
    """
    Least-Squares Complex Frequency-domain estimate.
    """
    def __init__(self, frf, freq, lower, upper, pol_order_high):
        """
        frf - FRF pri vseh lokacijah in frekvencah
        freq - 1D array frekvenc
        lower - najbolj spodnja opazovana frekvenca
        upper - najbolj zgornja opazovana frekvenca
        """
        sel_in = (freq > lower) & (freq < upper)
        sel_low = (freq < upper)

        self.frf = np.asarray(frf)
        self.frf_in = self.frf[:, sel_in]        

        self.lower = lower
        self.upper = upper
        self.pol_order_high = pol_order_high

        self.freq = freq
        self.freq_in = freq[sel_in]
        self.freq_low = freq[sel_low]

        self.omega = 2*np.pi*freq
        self.omega_in = self.omega[sel_in]
        self.omega_low = self.omega[sel_low]

        self.sampling_time = 1/(2*self.freq[-1])

        # Odstranjevanje spodnjega dela spektra
        # lower_ind = np.argmin(np.abs(freq - lower))
        # self.frf_low = irfft_adjusted_lower_limit(frf, lower_ind, np.arange(-frf.shape[1], frf.shape[1]+1))

        ########################################################################
        # plt.semilogy(freq, np.abs(self.frf_low_1), label='1')
        # plt.semilogy(freq, np.abs(self.frf_low_2[0]), '.-', label='2')
        # plt.figure()
        # plt.semilogy(freq, np.abs(self.frf_low[0]), label='Low')
        # plt.semilogy(freq, np.abs(self.frf[0]), label='Orig')
        # plt.legend()

        # print(self.frf_low.shape)
        ########################################################################

        

        # self.frf = np.asarray(frf) #frekenčne prenosne funkcije
        # self.freq = freq #frekvence (vse!)
        # self.omega = 2* np.pi * self.freq #krožne frekvence
        
        # self.select_freq = (self.freq >= self.lower) & (self.freq <= self.upper) #omejimo frekvence na zgornjo in spodnjo
        # self.sel_clip_up = (self.freq >= 0) & (self.freq <= self.upper)#odstranimo zgornje frekvence
        # self.sel_lower = (self.freq >= 0) & (self.freq <= self.lower)#izberemo samo spodnje frekvence
        
        # self.freq_sel = self.freq[self.sel_clip_up]
        # self.omega_sel = self.omega[self.select_freq]
        
        # self.samp_time = 1/(2 * self.freq_sel[-1]-self.freq_sel[0])
        
        
        # self.frf_sel = self.frf[::1, self.sel_clip_up]
        # self.frf_sel[:, self.sel_lower[:self.frf_sel.shape[1]]] = 0

        # self.frf_in = self.frf[:, self.select_freq]
        
    def get_poles_old(self):
        # self.poles = []
        # self.f_poles = []
        # self.ceta = []
        # self.cetaT = []

        self.all_poles = []
        self.pole_freq = []
        self.pole_xi = []
        
        for n in tqdm(range(self.pol_order_low, self.pol_order_high)):
            M = np.zeros((n+1, n+1), dtype=complex)
            for Ho_ in self.frf_low:
                S_fft = -1/(len(Ho_)) * np.real(np.fft.fft(Ho_, 2*len(Ho_)))
                T_fft = 1/(len(Ho_)) * np.real(np.fft.fft(np.abs(Ho_)**2, 2*len(Ho_)))

                S_col = S_fft[:n+1]
                S_row = np.append(S_fft[-n:], S_fft[0])[::-1] 
                T_col = T_fft[:n+1]

                S = scipy.linalg.toeplitz(S_col, S_row) #S ni simetričen
                T = scipy.linalg.toeplitz(T_col, T_col) #T je simetričen
                R = np.identity(np.size(S, axis=0))     #če ne uporabljamo uteži je R enotska matrika

                M += T - S.T @ np.linalg.inv(R) @ S
            
            M = 2 * M

            A = M[:n, :n]
            B = -M[:n, n]

            x = np.linalg.inv(A) @ np.vstack(B)
            est_alfa = np.append(x, 1)
            # est_beta = -np.linalg.inv(R) @ S @ est_alfa

            roots = np.roots(est_alfa[::-1])
            poles = -np.log(roots)/self.sampling_time
            # poles = 1/self.sampling_time * (np.log(np.abs(roots)) - 1j * np.angle(roots)) 

            f_pole = np.imag(poles)/(2*np.pi)
            ceta = -np.real(poles) / np.abs(poles)
            # cetaT = -np.real(poles) / np.abs(poles)

            self.all_poles.append(poles)
            self.pole_freq.append(f_pole)
            self.pole_xi.append(ceta)
            # self.cetaT.append(cetaT)
        
        # Fast stab chart
        # fig, ax1 = plt.subplots(figsize=(10, 4))
        # ax2 = ax1.twinx()
        # plt.xlim(0, self.upper)
        # ax2.semilogy(self.freq, np.average(np.abs(self.frf), axis=0), alpha=0.7, color='k')
        # ax1.plot(self.pole_freq[-1], np.repeat(50, len(self.pole_freq[-1])), 'o')

    def get_poles(self):
        """Narejeno na podlagi Blažove in Jakove kode."""
        self.all_poles = []
        self.pole_freq = []
        self.pole_xi = []

        lower_ind = np.argmin(np.abs(self.freq - self.lower))
        n = self.pol_order_high * 2
        nf = 2 * (self.frf.shape[1] - 1)
        nr = self.frf.shape[0]

        indices_s = np.arange(-n, n+1)
        indices_t = np.arange(n+1)

        sk = -irfft_adjusted_lower_limit(self.frf, lower_ind, indices_s)
        t = irfft_adjusted_lower_limit(self.frf.real**2 + self.frf.imag**2, lower_ind, indices_t)
        r = -(np.fft.irfft(np.ones(lower_ind), n=nf))[indices_t]*nf
        r[0] += nf

        s = []
        for i in range(nr):
            s.append(toeplitz(sk[i, n:], sk[i, :n+1][::-1]))
        t = toeplitz(np.sum(t[:, :n+1], axis=0))
        r = toeplitz(r)

        sr_list = []
        for j in range(2, n+1, 2):
            d = 0
            for i in range(nr):
                rinv = np.linalg.inv(r[:j+1, :j+1])
                snew = s[i][:j+1, :j+1]
                d -= np.dot(np.dot(snew[:j+1, :j+1].T, rinv), snew[:j+1, :j+1])   # sum
            d += t[:j+1, :j+1]

            a0an1 = np.linalg.solve(-d[0:j, 0:j], d[0:j, j])
            sr = np.roots(np.append(a0an1, 1)[::-1])  # the numerator coefficients

            poles = -np.log(sr) / self.sampling_time  # Z-domain (for discrete-time domain model)
            f_pole = np.imag(poles)/(2*np.pi)
            ceta = -np.real(poles) / np.abs(poles)

            self.all_poles.append(poles)
            self.pole_freq.append(f_pole)
            self.pole_xi.append(ceta)

        # Fast stab chart
        # fig, ax1 = plt.subplots(figsize=(10, 4))
        # ax2 = ax1.twinx()
        # plt.xlim(0, self.upper)
        # ax2.semilogy(self.freq, np.average(np.abs(self.frf), axis=0), alpha=0.7, color='k')
        # ax1.plot(self.pole_freq[-1], np.repeat(50, len(self.pole_freq[-1])), 'o')


    def stab_chart(self, poles, fn_temp=0.001, xi_temp=0.05, legend=False, latex_render=False, title=None):
        """
        Prikaz stabilizacijskega diagrame.

        Podaja možnost interaktivnega izbiranja polov. Ko izberemo pol se sproti izvaja identifikacija.
        Identifikacijo lahko izvajamo tudi na podlagi že poznanih približkov polov in jih vnesemo direktno v funkcijo `identifikacija()`

        Možnost 1:
        >>> a.stab_chart()
        >>> a.nat_freq #lastne frekvence
        >>> a.nat_ceta #modalno dušenje

        Možnost 2:
        >>> a.stab_chart()
        >>> priblizki = [234, 545]
        >>> a.identification(priblizki)
        >>> a.nat_freq #lastne frekvence
        >>> a.nat_ceta #modalno dušenje
        """
        Nmax = self.pol_order_high
        fn_temp, xi_temp, test_fn, test_xi = stabilisation(poles, Nmax, err_fn=fn_temp, err_xi=xi_temp)

        fig, ax1 = plt.subplots(figsize=(10, 4))
        ax2 = ax1.twinx()
        plt.xlim(self.lower, self.upper)
        
        ax1.set_xlabel(r'$f$ [Hz]', fontsize=12)
        ax1.set_ylabel(r'Polynom order', fontsize=12)
        ax2.set_ylabel(r'$|\alpha|$', fontsize=12)
        
        if latex_render is True:
            plt.rc('text', usetex=True)
            plt.rc('font', family='serif')
            ax1.tick_params(axis='both', which='major', labelsize=12)
            ax2.tick_params(axis='both', which='major', labelsize=12)
            ax1.set_xlabel(r'$f$ [Hz]', fontsize=12)
            ax1.set_ylabel(r'Red polinoma', fontsize=12)
            ax2.set_ylabel(r'$|\alpha|_{log}$', fontsize=12)
            ax1.set_xlim([self.lower, self.upper])
        
        a=np.argwhere((test_fn>0) & (test_xi==0)) # stable eigenfrequencues, unstable damping ratios
        b=np.argwhere((test_fn>0) & (test_xi>0) ) # stable eigenfrequencies, stable damping ratios
        c=np.argwhere((test_fn==0) & (test_xi==0)) # unstable eigenfrequencues, unstable damping ratios
        d=np.argwhere((test_fn==0) & (test_xi>0)) # unstable eigenfrequencues, stable damping ratios

        for i in range(0,len(a)):
            p1 = ax1.plot(fn_temp[a[i,0], a[i,1]], 1+a[i,1], c='b', marker='x',markersize=3)
        for j in range(0,len(b)):
            p2 = ax1.plot(fn_temp[b[j,0], b[j,1]] ,1+b[j,1], c='g', marker='x',markersize=4)
        for k in range(0,len(c)):
            p3 = ax1.plot(fn_temp[c[k,0], c[k,1]], 1+c[k,1], c='r', marker='.',markersize=3)
        for l in range(0,len(d)):
            p4 = ax1.plot(fn_temp[d[l,0], d[l,1]], 1+d[l,1], c='r', marker='*',markersize=3)
        
        if legend:
            p1 = ax1.plot(fn_temp[a[i,0], a[i,1]], 1+a[i,1],'x', c='b', markersize=3,label = "stable frequency, unstable damping")
            p2 = ax1.plot(fn_temp[b[j,0], b[j,1]] ,1+b[j,1],'x', c='g', markersize=4,label = "stable frequency, stable damping")
            p3 = ax1.plot(fn_temp[c[k,0], c[k,1]], 1+c[k,1],'.', c='r', markersize=3,label = "unstable frequency, unstable damping")
            p4 = ax1.plot(fn_temp[d[l,0], d[l,1]], 1+d[l,1],'*', c='r', markersize=3,label = "unstable frequency, stable damping")
            ax1.legend(loc = 'best')

        ax2.semilogy(self.freq, np.average(np.abs(self.frf), axis=0), alpha=0.7, color='k')
        ax1.grid(True)

        print('Za izbiranje lastnih frekvenc uporabi SREDNJI gumb.\nZa izbris zadnje točke uporabi DESNI gumb.')
        self.nat_freq = []
        self.nat_xi = []
        self.pole_ind = []
        
        line, = ax1.plot(self.nat_freq, np.repeat(self.pol_order_high, len(self.nat_freq)), 'kv', markersize=8)
        def onclick(event):
            if event.button == 2: #če smo pritisnili gumb 2 (srednji na miški)
                self.identification([event.xdata], self.nat_freq, self.nat_xi, self.pole_ind) #identifikacija lastnih frekvenc in dušenja
                print(f'{len(self.nat_freq)}. frekvenca: ~{int(np.round(event.xdata))} --> {self.nat_freq[-1]} Hz')
            elif event.button == 3:
                try:
                    del self.nat_freq[-1] #izbrišemo zadnjo točko
                    del self.nat_xi[-1]
                    del self.pole_ind[-1]
                    print('Izbrisana zadnja točka...')
                except:
                    pass

            line.set_xdata(np.asarray(self.nat_freq)) #posodobimo podatke
            line.set_ydata(np.repeat(Nmax*1.04, len(self.nat_freq)))
            fig.canvas.draw() 

        cid = fig.canvas.mpl_connect('button_press_event', onclick)
        
        if title is not None:
            plt.savefig(title)

    def identification(self, approx_nat_freq, nat_freq=None, nat_xi=None, pole_ind=None):
        pole_ind = []
        for i, fr in enumerate(approx_nat_freq):
            sel = np.argmin(np.abs(self.pole_freq[-1] - fr))
            pole_ind.append(np.argmin(np.abs(self.pole_freq[-1] - self.pole_freq[-1][sel])))

        if nat_freq is None and nat_xi is None:
            self.nat_freq = self.pole_freq[-1][pole_ind]
            self.nat_xi = self.pole_xi[-1][pole_ind]
            self.pole_ind = pole_ind
        else:
            nat_freq.append(self.pole_freq[-1][pole_ind][0])
            nat_xi.append(self.pole_xi[-1][pole_ind][0])
            self.pole_ind.append(pole_ind[0])
            self.nat_freq = nat_freq
            self.nat_xi = nat_xi

    ######################################################################################
    def modal_constants(self, whose_poles='own'):
        ndim = self.frf_in.ndim
        if whose_poles == 'own':
            poles = self.all_poles[-1][self.pole_ind]
            n_poles = len(self.pole_ind)
        else:
            poles = whose_poles.all_poles[-1][whose_poles.pole_ind]
            n_poles = len(whose_poles.pole_ind)
        
        w = np.append(-self.omega[1:][::-1], self.omega[1:])
        alpha = np.append(self.frf[:, 1:].conjugate()[:, ::-1], self.frf[:, 1:], ndim-1)
        TA = np.ones([len(w), n_poles+2], complex)

        for n in range(n_poles):
            TA[:, n] = 1/(1j*w - poles[n])
        TA[:, -2] = -1/w**2
        TA[:, -1] = np.ones_like(w)
        AT = np.linalg.pinv(TA)

        if ndim == 1:
            A_LSFD = np.dot(AT, self.frf)
        elif ndim == 2:
            IO = self.frf.shape[0]
            A_LSFD = np.zeros([IO, n_poles+2], complex)
            for v in range(IO):
                A_LSFD[v, :] = np.dot(AT, alpha[v, :])
        self.A_LSFD = A_LSFD
        self.poles = poles
        return A_LSFD

    def FRF_reconstruct(self, FRF_ind): 
        FRF_true = np.zeros(len(self.omega), complex)
        for n in range(self.A_LSFD.shape[1]-2):
            FRF_true += (self.A_LSFD[FRF_ind, n] / (1j*self.omega - self.poles[n]))

        FRF_true += -self.A_LSFD[FRF_ind, -2]/(self.omega**2) + self.A_LSFD[FRF_ind, -1]
        return FRF_true

    def lsfd(self, whose_poles):
        """
        LSFD (Least-Squares Frequency domain) method is used in order
        to determine the residues and mode shapes from complex natural frquencies
        and the measured frequency response functions.
        :param lambdak: a vector of selected complex natural frequencies
        :param f: frequecy vector
        :param frf: frequency response functions
        :return: reconstructed FRF, modal constant(residue), lower residual, upper residual

        Source: https://github.com/openmodal/OpenModal/blob/master/OpenModal/analysis/lsfd.py
        """
        frf = self.frf
        f = self.freq
        lambdak = whose_poles.all_poles[-1][whose_poles.pole_ind]

        ndim = frf.ndim
        if ndim == 3:
            ni = frf.shape[0]  # number of references
            no = frf.shape[1]  # number of responses
            n = frf.shape[2]   # length of frequency vector
        elif ndim == 2:
            ni = 1
            no = frf.shape[0]
            n = frf.shape[1]
        nmodes = lambdak.shape[0]  # number of modes

        omega = 2 * np.pi * f  # angular frequency

        # Factors in the freqeuncy response function
        b = 1 / np.subtract.outer(1j * omega, lambdak).T
        c = 1 / np.subtract.outer(1j * omega, np.conj(lambdak)).T

        # Separate complex data to real and imaginary part
        hr = frf.real
        hi = frf.imag
        br = b.real
        bi = b.imag
        cr = c.real
        ci = c.imag

        # Stack the data together in order to obtain 2D matrix
        hri = np.dstack((hr, hi))
        bri = np.hstack((br+cr, bi+ci))
        cri = np.hstack((-bi+ci, br-cr))

        ur_multiplyer = np.ones(n)
        ur_zeros = np.zeros(n)
        lr_multiplyer = -1/(omega**2)

        urr = np.hstack((ur_multiplyer, ur_zeros))
        uri = np.hstack((ur_zeros, ur_multiplyer))
        lrr = np.hstack((lr_multiplyer, ur_zeros))
        lri = np.hstack((ur_zeros, lr_multiplyer))

        bcri = np.vstack((bri, cri, urr, uri, lrr, lri))

        # Reshape 3D array to 2D for least squares coputation
        hri = hri.reshape(ni*no, 2*n)

        # Compute the modal constants (residuals) and upper and lower residuals
        uv, _, _, _ = np.linalg.lstsq(bcri.T,hri.T, rcond=None)

        # Reshape 2D results to 3D
        uv = uv.T.reshape(ni, no, 2*nmodes+4)

        u = uv[:, :, :nmodes]
        v = uv[:, :, nmodes:-4]
        urr = uv[:, :, -4]
        uri = uv[:, :, -3]
        lrr = uv[:, :, -2]
        lri = uv[:, :, -1]

        a = u + 1j * v  # Modal constant (residue)
        ur = urr + 1j * uri  # Upper residual
        lr = lrr + 1j * lri  # Lower residual

        # Reconstructed FRF matrix
        h = np.dot(uv, bcri)
        h = h[:, :, :n] + 1j * h[:, :, n:]

        return h, a, lr, ur
    ######################################################################################
    # Stara koda
    def modal_const(self, frf_loc, whos_poles='own', whos_inds='own', form = 'accelerance'):
        self.frf_loc = frf_loc
        if whos_poles =='own':
            poles = self.poles[-1][self.pole_ind]
            n_poles = len(self.pole_ind)
        else:
            poles = whos_poles.poles[-1][whos_poles.pole_ind]
            n_poles = len(whos_poles.pole_ind)

        poles_mk = np.concatenate((poles, np.conj(poles)))

        mk1 = self.frf[self.frf_loc, self.select_freq]
        mk2 = np.zeros((len(self.omega_sel), 2*n_poles+2), dtype=complex)
        for i in range(2*n_poles+2):
            if i<2*n_poles:
                mk2[:, i] = 1/(1j * self.omega_sel - poles_mk[i])
            elif i==2*n_poles:
                mk2[:, i] = -1/(self.omega_sel**2) #lower residual
            elif i==2*n_poles+1:
                mk2[:, i] = 1 #upper residual


        mk2_m = np.ma.masked_invalid(mk2)
        mk2_mask = np.ma.getmask(mk2_m)
        mk2_m[mk2_mask] = 0

        self.mk2 = np.copy(mk2_m)
        self.mk3 = np.linalg.pinv(self.mk2) @ mk1.T
    
    def reconstruct(self, whos_poles='own', whos_inds='own'):
        if whos_poles =='own':
            poles = self.poles[-1][self.pole_ind]
            n_poles = len(self.pole_ind)
        else:
            poles = whos_poles.poles[-1][whos_poles.pole_ind]
            n_poles = len(whos_poles.pole_ind)
            
        poles_mk = np.concatenate((poles, np.conj(poles)))
        
        rek2 = np.zeros((len(self.omega[self.sel_clip_up]), 2*n_poles+2), dtype=complex)
        for i in range(2*n_poles+2):
            if i<2*n_poles:
                rek2[:, i] = 1/(1j * self.omega[self.sel_clip_up] - poles_mk[i])
            elif i==2*n_poles:
                rek2[:, i] = -1/(self.omega[self.sel_clip_up]**2)
            elif i==2*n_poles+1:
                rek2[:, i] = 1
                
        self.rek = rek2 @ self.mk3 #rekonstrukcija
        self.rekf = self.freq[self.sel_clip_up] #freq vektor rekonstrukcije
    ######################################################################################
        
def complex_freq_to_freq_and_damp(sr):
    """
    Convert the complex natural frequencies to natural frequencies and the
    corresponding dampings.

    :param sr: complex natural frequencies
    :return: natural frequency and damping
    """

    fr = np.abs(sr)
    xir = -sr.real/fr
    fr /= (2 * np.pi)

    return fr, xir

def redundant_values(omega, xi, prec):
    """
    This function supresses the redundant values of frequency and damping
    vectors, which are the consequence of conjugate values

    Input:
        omega - eiqenfrquencies vector
        xi - damping ratios vector
        prec - absoulute precision in order to distinguish between two values

    @author: Blaz Starc
    @contact: blaz.starc@fs.uni-lj.si
    """
    N = len(omega)
    test_omega = np.zeros((N,N), dtype='int')
    for i in range(1,N):
        for j in range(0,i):
            if np.abs((omega[i] - omega[j])) < prec:
                test_omega[i,j] = 1
            else: test_omega[i,j] = 0
    test = np.zeros(N, dtype = 'int')
    for i in range(0,N):
        test[i] = np.sum(test_omega[i,:])
    
    omega_mod = omega[np.argwhere(test<1)]
    xi_mod = xi[np.argwhere(test<1)]
    return omega_mod, xi_mod

def stabilisation(sr, nmax, err_fn, err_xi):
    """
    A function that computes the stabilisation matrices needed for the
    stabilisation chart. The computation is focused on comparison of
    eigenfrequencies and damping ratios in the present step 
    (N-th model order) with the previous step ((N-1)-th model order). 
    
    :param sr: list of lists of complex natrual frequencies
    :param n: maximum number of degrees of freedom
    :param err_fn: relative error in frequency
    :param err_xi: relative error in damping

    :return fn_temap eigenfrequencies matrix
    :return xi_temp: updated damping matrix
    :return test_fn: updated eigenfrequencies stabilisation test matrix
    :return test_xi: updated damping stabilisation test matrix
    
    @author: Blaz Starc
    @contact: blaz.starc@fs.uni-lj.si
    """

    # TODO: check this later for optimisation # this doffers by LSCE and LSCF
    fn_temp = np.zeros((2*nmax, nmax), dtype = 'double')
    xi_temp = np.zeros((2*nmax, nmax), dtype = 'double')
    test_fn = np.zeros((2*nmax, nmax), dtype = 'int')
    test_xi = np.zeros((2*nmax, nmax), dtype = 'int')

    for nr, n in enumerate(range(nmax)):
        fn, xi = complex_freq_to_freq_and_damp(sr[nr])
        fn, xi = redundant_values(fn, xi, 1e-3) # elimination of conjugate values in
                                                # order to decrease computation time
        if n == 1:
            # first step
            fn_temp[0:len(fn), 0:1] = fn
            xi_temp[0:len(fn), 0:1] = xi

        else:
            # Matrix test is created for comparison between present(N-th) and
            # previous (N-1-th) data (eigenfrequencies). If the value equals:
            # --> 1, the data is within relative tolerance err_fn
            # --> 0, the data is outside the relative tolerance err_fn
            fn_test = np.zeros((len(fn), len(fn_temp[:, n - 1])), dtype ='int')
            for i in range(0, len(fn)):
                for j in range(0, len(fn_temp[0:2*(n), n-1])):
                    if fn_temp[j, n-2] ==  0:
                        fn_test[i,j] = 0
                    else:
                        if np.abs((fn[i] - fn_temp[j, n-2])/fn_temp[j, n-2]) < err_fn:
                            fn_test[i,j] = 1
                        else: fn_test[i,j] = 0

            for i in range(0, len(fn)):
                test_fn[i, n - 1] = np.sum(fn_test[i, :]) # all rows are summed together

            # The same procedure as for eigenfrequencies is applied for damping
            xi_test = np.zeros((len(xi), len(xi_temp[:, n - 1])), dtype ='int')
            for i in range(0, len(xi)):
                for j in range(0, len(xi_temp[0:2*(n), n-1])):
                    if xi_temp[j, n-2]==0:
                        xi_test[i,j] = 0
                    else:
                        if np.abs((xi[i] - xi_temp[j, n-2])/xi_temp[j, n-2]) < err_xi:
                            xi_test[i,j] = 1
                        else: xi_test[i,j] = 0
            for i in range(0, len(xi)):
                test_xi[i, n - 1] = np.sum(xi_test[i, :])

            # If the frequency/damping values corresponded to the previous iteration,
            # a mean of the two values is computed, otherwise the value stays the same
            for i in range(0, len(fn)):
                for j in range(0, len(fn_temp[0:2*(n), n-1])):
                    if fn_test[i,j] == 1:
                        fn_temp[i, n - 1] = (fn[i] + fn_temp[j, n - 2]) / 2
                    elif fn_test[i,j] == 0:
                        fn_temp[i, n - 1] = fn[i]
            for i in range(0, len(fn)):
                for j in range(0, len(fn_temp[0:2*(n), n-1])):
                    if xi_test[i,j] == 1:
                        xi_temp[i, n - 1] = (xi[i] + xi_temp[j, n - 2]) / 2
                    elif xi_test[i,j] == 0:
                        xi_temp[i, n - 1] = xi[i]

    return fn_temp, xi_temp, test_fn, test_xi

def irfft_adjusted_lower_limit(x, low_lim, indices):
    """
    Compute the ifft of real matrix x with adjusted summation limits:
        y(j) = sum[k=-n-2, ... , -low_lim-1, low_lim, low_lim+1, ... n-2,
                   n-1] x[k] * exp(sqrt(-1)*j*k* 2*pi/n),
        j =-n-2, ..., -low_limit-1, low_limit, low_limit+1, ... n-2, n-1
    :param x: Single-sided real array to Fourier transform.
    :param low_lim: lower limit index of the array x.
    :param indices: list of indices of interest
    :return: Fourier transformed two-sided array x with adjusted lower limit.
             Retruns values.

    Source: https://github.com/openmodal
    """

    nf = 2 * (x.shape[1] - 1)
    a = (np.fft.irfft(x, n=nf)[:, indices]) * nf
    b = (np.fft.irfft(x[:, :low_lim], n=nf)[:, indices]) * nf
    # plt.figure()
    # plt.plot(a[3])
    # plt.plot(a[3]-b[3])
    # return np.fft.rfft(a - b, n=nf) / nf
    return a - b






















































