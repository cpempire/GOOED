
from __future__ import absolute_import, division, print_function

import dolfin as dl
import numpy.matlib
import math
import numpy as np
from itertools import combinations 
import scipy
import matplotlib.pyplot as plt
import mshr as ms
import time

import sys
import os

sys.path.append( os.environ.get('HIPPYLIB_BASE_DIR', "../..") + "/applications/ad_diff/" )
from model_ad_diff import TimeDependentAD, SpaceTimePointwiseStateObservation
sys.path.append( os.environ.get('HIPPYLIB_BASE_DIR', "../../") )
from hippylib import *

import logging
logging.getLogger('FFC').setLevel(logging.WARNING)
logging.getLogger('UFL').setLevel(logging.WARNING)
dl.set_log_active(False)

seed = 1
np.random.seed(seed=seed)


        

class Hd_rho_op:

    def __init__(self, problem,problem2,Q,Qoper,Gamma_z):
        """
        Construct the Jacobian operator
        """
        self.problem = problem
        self.problem2 = problem2
        self.misfit = problem.misfit
        self.misfit2 = problem2.misfit
        self.u_snapshot = dl.Vector()
        self.uhat = problem2.generate_vector(STATE)
        self.Bv = problem2.generate_vector(ADJOINT)
        self.FCprv = problem2.generate_vector(STATE)
        self.rhs_fwd = self.problem2.generate_vector(STATE)
        self.Q = Q
        self.Qoper = Qoper
        self.Gamma_z = Gamma_z

    def init_vector(self, x):

        self.problem.misfit.B.init_vector(x,0)             
        
    def mult(self,x,y):
        for t in self.misfit.observation_times:
            self.misfit.B.init_vector(self.u_snapshot, 1)
            self.misfit.B.transpmult(x, self.u_snapshot) 
            self.Bv.store(self.u_snapshot, t)
        #A^-TB^Tv
        phat = self.problem.generate_vector(ADJOINT)
        self.problem.solveAdjIncremental(phat, self.Bv)
        #C^T A^-TB^Tv
        v = self.problem.generate_vector(PARAMETER)
        self.problem.applyCt(phat, v)

        Cprv = self.problem.generate_vector(PARAMETER)
        self.problem.prior.Rsolver.solve(Cprv,v)
        self.problem2.applyC(Cprv, self.rhs_fwd)

        self.problem2.solveFwdIncremental(self.FCprv,self.rhs_fwd)
        for t in self.misfit2.observation_times:
            self.FCprv.retrieve(self.u_snapshot, t)
        tmp = self.Q.inner(self.u_snapshot)
        tmp *= 1./self.Gamma_z
        for t in self.misfit2.observation_times:
            self.Qoper.store(self.Q*tmp,t)

        AtQ = self.problem2.generate_vector(ADJOINT)
        self.problem2.solveAdjIncremental(AtQ, self.Qoper)
        FtQ = self.problem2.generate_vector(PARAMETER)
        self.problem2.applyCt(AtQ, FtQ)
        CprFtQ = self.problem2.generate_vector(PARAMETER)
        self.problem.prior.Rsolver.solve(CprFtQ,FtQ)

        v = CprFtQ
        self.problem.applyC(v, self.rhs_fwd)
        self.problem.solveFwdIncremental(self.uhat, self.rhs_fwd)
        # Gv2 = dl.Vector(self.misfit.B.mpi_comm())
        for t in self.misfit.observation_times:
            self.uhat.retrieve(self.u_snapshot, t)
            self.misfit.B.mult(self.u_snapshot, y)


class delta_Hd_op:

    def __init__(self, problem,problem2,Q,Qoper,Gamma_z):
        """
        Construct the Jacobian operator
        """
        self.problem = problem
        self.problem2 = problem2
        self.misfit = problem.misfit
        self.misfit2 = problem2.misfit
        self.u_snapshot = dl.Vector()
        self.uhat = problem2.generate_vector(STATE)
        self.Bv = problem2.generate_vector(ADJOINT)
        self.FCprv = problem2.generate_vector(STATE)
        self.rhs_fwd = self.problem2.generate_vector(STATE)
        self.Q = Q
        self.Qoper = Qoper
        self.Gamma_z = Gamma_z

    def init_vector(self, x):

        self.problem.misfit.B.init_vector(x,0)             
        
    def mult(self,x,y):
        for t in self.misfit.observation_times:
            self.misfit.B.init_vector(self.u_snapshot, 1)
            self.misfit.B.transpmult(x, self.u_snapshot) 
            self.Bv.store(self.u_snapshot, t)
        #A^-TB^Tv
        phat = self.problem.generate_vector(ADJOINT)
        self.problem.solveAdjIncremental(phat, self.Bv)
        #C^T A^-TB^Tv
        v = self.problem.generate_vector(PARAMETER)
        self.problem.applyCt(phat, v)

        Cprv = self.problem.generate_vector(PARAMETER)
        self.problem.prior.Rsolver.solve(Cprv,v)
        self.problem2.applyC(Cprv, self.rhs_fwd)

        self.problem2.solveFwdIncremental(self.FCprv,self.rhs_fwd)
        for t in self.misfit2.observation_times:
            self.FCprv.retrieve(self.u_snapshot, t)
        tmp = self.Q.inner(self.u_snapshot)
        tmp *= 1./self.Gamma_z
        for t in self.misfit2.observation_times:
            self.Qoper.store(self.Q*tmp,t)

        AtQ = self.problem2.generate_vector(ADJOINT)
        self.problem2.solveAdjIncremental(AtQ, self.Qoper)
        FtQ = self.problem2.generate_vector(PARAMETER)
        self.problem2.applyCt(AtQ, FtQ)
        CprFtQ = self.problem2.generate_vector(PARAMETER)
        self.problem.prior.Rsolver.solve(CprFtQ,FtQ)

        v = Cprv
        self.problem.applyC(v, self.rhs_fwd)
        self.problem.solveFwdIncremental(self.uhat, self.rhs_fwd)
        Gv1 = dl.Vector(self.misfit.B.mpi_comm())
        for t in self.misfit.observation_times:
            self.uhat.retrieve(self.u_snapshot, t)
            self.misfit.B.mult(self.u_snapshot, Gv1)

        v = CprFtQ
        self.problem.applyC(v, self.rhs_fwd)
        self.problem.solveFwdIncremental(self.uhat, self.rhs_fwd)
        Gv2 = dl.Vector(self.misfit.B.mpi_comm())
        for t in self.misfit.observation_times:
            self.uhat.retrieve(self.u_snapshot, t)
            self.misfit.B.mult(self.u_snapshot, Gv2)
        y.axpy(1.,Gv1-Gv2)



################################################################
def D_op(ur_index,misfit,Gamma_z,FtQt):
    [u,m,p] = problem.generate_vector()
    problem.solveFwd(u, [u,m,p])
    problem.solveAdj(p, [u,m,p])
    mg = problem.generate_vector(PARAMETER)
    grad_norm = problem.evalGradientParameter([u,m,p], mg)

    d, U, H,misfit = ComputeHessianEvalue(misfit,Vh,observation_times,ur_index,noise_std_dev,mesh,prior,simulation_times,wind_velocity,r,x)


    posterior = GaussianLRPosterior( prior, d, U )

    H.misfit_only = False

    solver = CGSolverSteihaug()
    # solver.set_operator(H2)
    solver.set_operator(H)
    solver.set_preconditioner( posterior.Hlr )
    solver.parameters["print_level"] = 0
    solver.parameters["rel_tolerance"] = 1e-6
    solver.solve(m, -mg)
    problem.solveFwd(u, [u,m,p])


    posterior.mean = m
    # #P Cpost P^*
    sol = problem.generate_vector(PARAMETER)

    posterior.Hlr.solve(sol,FtQt)

    misfit2 = SpaceTimePointwiseStateObservation(Vh, prediction_times, targets[ur_index])
    misfit2.noise_variance = noise_std_dev*noise_std_dev


    rhs_fwd = problem2.generate_vector(STATE)
    problem.applyC(sol, rhs_fwd)
    uhat = problem2.generate_vector(STATE)
    problem2.solveFwdIncremental(uhat, rhs_fwd)
    u_snapshot = dl.Vector()
    misfit2.B.init_vector(u_snapshot, 1)
    # out = problem.generate_vector(STATE)
    for t in misfit2.observation_times:
        uhat.retrieve(u_snapshot, t)
        # out.store(self.u_snapshot, t)
    Dop1 = Q.inner(u_snapshot)


    Dop2 = Gamma_z
    Dop = 0.5*(np.log(Dop2/Dop1))
    # Dop = 0.5*(np.log(Dop1))



    return Dop   




def ComputeHessianEvalue(misfit,Vh,observation_times,ur_index,noise_std_dev,mesh,prior,simulation_times,wind_velocity,r,x):
    misfit2 = SpaceTimePointwiseStateObservation(Vh, observation_times, targets[ur_index])
    misfit2.noise_variance = noise_std_dev*noise_std_dev
    problem = TimeDependentAD(mesh, [Vh,Vh,Vh], prior, misfit2, simulation_times, wind_velocity, True)
    r = len(ur_index)
    for t in range(misfit2.observation_times.shape[0]):
        misfit2.d.data[t][0:r]=misfit.d.data[t][ur_index]

    H2 = ReducedHessian(problem, 1e-12, misfit_only=True) 

    k = r
    p = 2
    # print( "Single Pass Algorithm. Requested eigenvectors: {0}; Oversampling {1}.".format(k,p) )
    Omega = MultiVector(x[PARAMETER], k+p)
    parRandom.normal(1., Omega)
    # lmbda, V = singlePassG(H, prior.R, prior.Rsolver, Omega, k)
    d, U = doublePassG(H2, prior.R, prior.Rsolver, Omega, k, s=1, check=False)

    return d,U,H2,misfit2


#####Construct the velocity field#########################

def v_boundary(x,on_boundary):
    return on_boundary

def q_boundary(x,on_boundary):
    return x[0] < dl.DOLFIN_EPS and x[1] < dl.DOLFIN_EPS

def computeVelocityField(mesh):
    Xh = dl.VectorFunctionSpace(mesh,'Lagrange', 2)
    Wh = dl.FunctionSpace(mesh, 'Lagrange', 1)
    if dlversion() <= (1,6,0):
        XW = dl.MixedFunctionSpace([Xh, Wh])
    else:
        mixed_element = dl.MixedElement([Xh.ufl_element(), Wh.ufl_element()])
        XW = dl.FunctionSpace(mesh, mixed_element)

    Re = 50#1e2

    g = dl.Expression(('0.0','(x[0] < 1e-14) - (x[0] > 1 - 1e-14)'), degree=1)
    bc1 = dl.DirichletBC(XW.sub(0), g, v_boundary)
    bc2 = dl.DirichletBC(XW.sub(1), dl.Constant(0), q_boundary, 'pointwise')
    bcs = [bc1, bc2]

    vq = dl.Function(XW)
    (v,q) = dl.split(vq)
    (v_test, q_test) = dl.TestFunctions (XW)

    def strain(v):
        return dl.sym(dl.nabla_grad(v))

    F = ( (2./Re)*dl.inner(strain(v),strain(v_test))+ dl.inner (dl.nabla_grad(v)*v, v_test)
           - (q * dl.div(v_test)) + ( dl.div(v) * q_test) ) * dl.dx

    dl.solve(F == 0, vq, bcs, solver_parameters={"newton_solver":
                                         {"relative_tolerance":1e-4, "maximum_iterations":100}})


    return v


#####Set up the mesh and finite element spaces#########################

mesh = dl.refine( dl.Mesh("ad_20.xml") )

wind_velocity = computeVelocityField(mesh)
Vh = dl.FunctionSpace(mesh, "Lagrange", 1)
para_dim = Vh.dim()
print( "Number of dofs: {0}".format( Vh.dim() ) )

#####Set up model (prior, true/proposed initial condition)#########################
ic_expr = dl.Expression('min(0.5,exp(-100*(pow(x[0]-0.35,2) +  pow(x[1]-0.7,2))))', element=Vh.ufl_element())
true_initial_condition = dl.interpolate(ic_expr, Vh).vector()


gamma = 1.
delta = 8.
prior = BiLaplacianPrior(Vh, gamma, delta, robin_bc=True)
print( "Prior regularization: (delta - gamma*Laplacian)^order: delta={0}, gamma={1}, order={2}".format(delta, gamma,2) )
prior.mean = dl.interpolate(dl.Constant(0.25), Vh).vector()



t_init         = 0.
t_final        = .8#4
dt             = .02#0.1
# observation_dt = .2

simulation_times = np.arange(t_init, t_final+.5*dt, dt)

observation_times = np.array([t_final])#np.arange(t_1, t_final+.5*dt, observation_dt)


ndim = 2

x1 = np.arange(0.1,1.,0.1)#np.array([0.2,0.55,0.8])
x2 = np.arange(0.1,1.,0.1)#np.array([0.25,0.5,0.75])

X1,X2 = np.meshgrid(x1, x2)
x_2d = np.array([X1.flatten('F'),X2.flatten('F')])
xtargets = x_2d.T
# ntargets = targets.shape[0]
targets = []
for i in range(xtargets.shape[0]):
    pt = xtargets[i]
    if pt[0] > 0.25 and pt[0] < 0.5 and pt[1] > 0.15 and pt[1] < 0.4:
        pass
    elif pt[0] > 0.6 and pt[0] < 0.75 and pt[1] > 0.6 and pt[1] < 0.85:
        pass
    else:
        targets.append(pt)
ntargets = len(targets)
targets = np.array(targets)




print ("Number of observation points: {0}".format(targets.shape[0]) )
misfit = SpaceTimePointwiseStateObservation(Vh, observation_times, targets)

problem = TimeDependentAD(mesh, [Vh,Vh,Vh], prior, misfit, simulation_times, wind_velocity, True)
problem.gauss_newton_approx = True


#####Generate the synthetic observations#########################
rel_noise = 0.01
utrue = problem.generate_vector(STATE)
x = [utrue, true_initial_condition, None]
problem.solveFwd(x[STATE], x, 1e-9)
misfit.observe(x, misfit.d)
MAX = misfit.d.norm("linf", "linf")
noise_std_dev = rel_noise * MAX
parRandom.normal_perturb(noise_std_dev,misfit.d)
misfit.noise_variance = noise_std_dev*noise_std_dev


#####Evaluate the gradient#########################
[u,m,p] = problem.generate_vector()
problem.solveFwd(u, [u,m,p], 1e-12)
problem.solveAdj(p, [u,m,p], 1e-12)
mg = problem.generate_vector(PARAMETER)
grad_norm = problem.evalGradientParameter([u,m,p], mg)

print( "(g,g) = ", grad_norm)
H = ReducedHessian(problem, 1e-12, misfit_only=True) 

k = ntargets
p = 2
Omega = MultiVector(x[PARAMETER], k+p)
parRandom.normal(1., Omega)
lmbda, V = doublePassG(H, prior.R, prior.Rsolver, Omega, k, s=1, check=False)
posterior = GaussianLRPosterior( prior, lmbda, V )
post_tr, _, _= posterior.trace(method="Randomized", r=300)
print("post trace:", post_tr)
## Check Cpost^-1Cpr


r = 10
rall = 20


H.misfit_only = False

solver = CGSolverSteihaug()
# solver.set_operator(H2)
solver.set_operator(H)
solver.set_preconditioner( posterior.Hlr )
solver.parameters["print_level"] = 1
solver.parameters["rel_tolerance"] = 1e-6
solver.solve(m, -mg)
problem.solveFwd(u, [u,m,p])


posterior.mean = m




# ############PredictionOfQoi##########################################

v = dl.TestFunction(Vh)
chi = dl.Expression('(x[0] > 0.23)*(x[0] < 0.52)*(x[1] > 0.13)*(x[1] < 0.42)', element=Vh.ufl_element())
# chi = dl.Expression('(x[0] > 0.58)*(x[0] < 0.77)*(x[1] > 0.58)*(x[1] < 0.87)', element=Vh.ufl_element())
# chi = dl.Expression('(x[0] > 0.58)*(x[0] < 0.77)*(x[1] > 0.58)*(x[1] < 0.87)+(x[0] > 0.23)*(x[0] < 0.52)*(x[1] > 0.13)*(x[1] < 0.42)', element=Vh.ufl_element())

Q = dl.assemble(v*chi*dl.dx)
t_init         = 0.
t_final        = 1.
dt             = .02


simulation_times2 = np.arange(t_init, t_final+.5*dt, dt)

prediction_times = np.array([t_final])#np.arange(t_1, t_final+.5*dt, observation_dt)


print ("Number of observation points: {0}".format(targets.shape[0]) )
misfit2 = SpaceTimePointwiseStateObservation(Vh, prediction_times, targets)

problem2 = TimeDependentAD(mesh, [Vh,Vh,Vh], prior, misfit2, simulation_times2, wind_velocity, True)
problem2.gauss_newton_approx = True


# #########################################################################


#Gamma_z = P Cpr P^* = QF Cpr F^* Q^*
# F^* Q^*
sol = problem.generate_vector(PARAMETER)
QT = problem2.generate_vector(PARAMETER)
QT = Q
Qoper = problem2.generate_vector(STATE)
for t in misfit2.observation_times:
    Qoper.store(QT,t)

AtQ = problem2.generate_vector(ADJOINT)
problem2.solveAdjIncremental(AtQ, Qoper)
FtQt = problem2.generate_vector(PARAMETER)
problem2.applyCt(AtQ, FtQt)
# Cpr F^*Q^*
CprFQ = dl.Vector()
prior.Rsolver.solve(CprFQ,FtQt)
# print(CprFQ.get_local())
# QF Cpr F^*Q^*
rhs_fwd = problem2.generate_vector(STATE)
problem2.applyC(CprFQ, rhs_fwd)
uhat = problem2.generate_vector(STATE)
problem2.solveFwdIncremental(uhat, rhs_fwd)
u_snapshot = dl.Vector()
misfit2.B.init_vector(u_snapshot, 1)
# out = problem.generate_vector(STATE)
for t in misfit2.observation_times:
    uhat.retrieve(u_snapshot, t)
    # out.store(self.u_snapshot, t)
Gamma_z = Q.inner(u_snapshot)
print("Gamma_z:", Gamma_z)
# G(Cpr P^* Gamma_z^-1 P Cpr)G^*v = G(Cpr F^*Q^* Gamma_z^-1 QF Cpr)G^*v


# ###Low-rank approximation of Hd_rho and delta_Hd



start = time.time()
l = rall
p = 2
k = 1
Hd_rho = Hd_rho_op(problem,problem2,Q,Qoper,Gamma_z)
delta_Hd = delta_Hd_op(problem,problem2,Q,Qoper,Gamma_z)
x_omega = dl.Vector()
Hd_rho.init_vector(x_omega)
Omega_l = MultiVector(x_omega, l+p)
Omega_k = MultiVector(x_omega, k+p)
parRandom.normal(1., Omega_l)
parRandom.normal(1., Omega_k)
zeta,U = doublePass(Hd_rho,Omega_k,k,s=1,check = False)
Gamma,V = doublePass(delta_Hd,Omega_l,l,s=1,check = False)
elapsed = time.time() - start
print("time",elapsed)
print("zeta", zeta)
print("Gamma",Gamma)
Vmatrix = np.zeros((ntargets,l))
for i in range(l):
    Vmatrix[:,i] = V[i].get_local()
Umatrix = np.zeros((ntargets,k))
for i in range(k):
    Umatrix[:,i] = U[i].get_local()
# print("U", Umatrix)
# print("V", Vmatrix)


u0 = Umatrix



print("ntargets",ntargets,"r:",r,"rall:",rall)
trace = []#np.zeros(Test)
det = []#np.zeros(Test)
sensor_all = []
test = 0

u = u0[:,0:rall]


########################################################################
print("swapping greedy")
ev = np.zeros(ntargets)
for i in range(ntargets):

    if rall > 1:
        ev[i] = np.linalg.norm(u[i,:])
    else:
        ev[i] = u[i]/np.linalg.norm(u)


# ev = np.arccos(ev)
sort_index = np.argsort(ev)[::-1]
ur_index = sort_index[0:r].copy()
ur_index_all = sort_index.copy()

ur = u[ur_index,:]
ur_all = u[ur_index_all,:]
converge = False
loop = 0
count_all = 0
max_loop = 10


Gamma_n = misfit.noise_variance * np.identity(r)
while loop < max_loop and not converge:
    count = 0
    for i in range(r):
        sensor_matrix = np.zeros((r,ntargets))
        for k in range(r):
            sensor_matrix[k][ur_index[k]] = 1


        
        Gamma_eta = Gamma_n + np.dot(sensor_matrix,np.dot(Vmatrix,np.dot(np.diag(Gamma),np.dot(Vmatrix.T,sensor_matrix.T))))



        # Gamma_eta = np.dot(sensor_matrix,np.dot(Gamma_eta_d,sensor_matrix.T))
        # print("Gamma_eta:",Gamma_eta)
        L = np.linalg.cholesky(np.linalg.inv(Gamma_eta))
        # print("L",L)
        # print("Hd",Hd)
        H = np.dot(sensor_matrix,np.dot(Umatrix,np.dot(np.diag(zeta),np.dot(Umatrix.T,sensor_matrix.T))))
        # H = np.dot(sensor_matrix,np.dot(Hd,sensor_matrix.T))
        # print("H",H)
        Ai = 0.5*np.log(np.linalg.det(np.identity(r)+np.dot(L.T,np.dot(H,L))))

        # Di = D_op(ur_index,misfit,Gamma_z,FtQt)
        for j in range(r,ntargets):
            ur_index_all_tmp = ur_index_all.copy()
            ur_index_all_tmp[[i,j]]=ur_index_all_tmp[[j,i]]
            ur_index_tmp = ur_index_all_tmp[0:r]



            sensor_matrix = np.zeros((r,ntargets))
            for k in range(r):
                sensor_matrix[k][ur_index_tmp[k]] = 1

            Gamma_eta = Gamma_n + np.dot(sensor_matrix,np.dot(Vmatrix,np.dot(np.diag(Gamma),np.dot(Vmatrix.T,sensor_matrix.T))))
            # Gamma_eta = np.dot(sensor_matrix,np.dot(Gamma_eta_d,sensor_matrix.T))
            # print("Gamma_eta:",Gamma_eta)
            L = np.linalg.cholesky(np.linalg.inv(Gamma_eta))
            # print("L",L)
            # print("Hd",Hd)
            H = np.dot(sensor_matrix,np.dot(Umatrix,np.dot(np.diag(zeta),np.dot(Umatrix.T,sensor_matrix.T))))
            # H = np.dot(sensor_matrix,np.dot(Hd,sensor_matrix.T))
            # print("H",H)
            Aj = 0.5*np.log(np.linalg.det(np.identity(r)+np.dot(L.T,np.dot(H,L))))
            # Dj = D_op(ur_index_tmp,misfit,Gamma_z,FtQt)
            # print(ur_index_all_tmp[[i,j]])
            # print(ur_index_all,Ai,Di)
            # print(ur_index_tmp,Aj,Dj)
            # dffd

            if Aj>Ai:#np.abs(Aj) > np.abs(Ai):
                count += 1
                ur_index_all = ur_index_all_tmp.copy()
                ur_index = ur_index_tmp.copy()
                Ai = Aj.copy()
    count_all += count
    loop += 1
    if count == 0:
        converge = True
    print("count of swap:",count)
print("count of swap all:",count_all)
print("number of loops:",loop)

sensor = np.sort(ur_index)

# trace.append(post_tr)
D = D_op(sensor,misfit,Gamma_z,FtQt)
det.append(D)
sensor_all.append(sensor)
print("sensor:",sensor)
print("EIG:", D)
fig = plt.figure(figsize=(6,5))



utrue.store(true_initial_condition, 0)

title_stamp = " at time {0}s" 

myu = dl.Function(Vh)
utrue.retrieve(myu.vector(),observation_times[0])


vmax = max( utrue.data[0].max(), misfit.d.data[0].max() )
vmin = min( utrue.data[0].min(), misfit.d.data[0].min() )
# nb.plot(myu, subplot_loc=121,  mytitle="True State",vmin=vmin, vmax=vmax)
# nb.plot_pts(targets, misfit.d.data[0], mytitle="Observations", subplot_loc=122, vmin=vmin, vmax=vmax)
nb.plot(myu,vmin=vmin, vmax=vmax,colorbar=False)#,mytitle=r'$t_{pred}=8.$')
plt.plot(targets[:,0],targets[:,1],color='#FDF5E6', marker='o',markerfacecolor="None",linestyle="None")
plt.plot(targets[sensor,0],targets[sensor,1],color='C1', marker='X',linestyle="None",markersize = 8)
plt.hlines(y=0.13, xmin=0.23, xmax=0.52,colors='y')
plt.hlines(y=0.42, xmin=0.23, xmax=0.52,colors='y')

# plt.hlines(y=0.58, xmin=0.58, xmax=0.77,colors='y')
# plt.hlines(y=0.87, xmin=0.58, xmax=0.77,colors='y')

plt.vlines(x=0.23, ymin=0.13, ymax=0.42,colors='y')
plt.vlines(x=0.52, ymin=0.13, ymax=0.42,colors='y')

# plt.vlines(x=0.58, ymin=0.58, ymax=0.87,colors='y')
# plt.vlines(x=0.77, ymin=0.58, ymax=0.87,colors='y')
filename0 = 'sensor_choice_'+ str(ntargets) + '_'+str(r)+ '_obs' +str(simulation_times[-1]) + '_pred' + str(t_final)+'.pdf'
# # nb.plot(dl.Function(Vh[STATE], utrue), mytitle="True State", subplot_loc=121, vmin=vmin, vmax=vmax)
# # nb.plot_pts(targets[sensor], misfit.d[sensor], mytitle="sensor", vmin=vmin, vmax=vmax)
# nb.plot_pts(targets[sensor], misfit.d.data[0][sensor], mytitle="sensor",vmin=vmin, vmax=vmax)
fig.savefig(filename0, format='pdf',bbox_inches='tight')
plt.close()



print("standard greedy")
ur_index = sort_index[0:r].copy()
ur_index_all = sort_index.copy()
ur = u[ur_index,:]
ur_all = u[ur_index_all,:]
count = 0
for i in range(r):
    sensor_matrix = np.zeros((i+1,ntargets))
    for k in range(i+1):
        sensor_matrix[k][ur_index[k]] = 1

    Gamma_n = misfit.noise_variance * np.identity(i+1)
    # Gamma_eta = np.dot(sensor_matrix,np.dot(Gamma_eta_d,sensor_matrix.T))
    Gamma_eta = Gamma_n + np.dot(sensor_matrix,np.dot(Vmatrix,np.dot(np.diag(Gamma),np.dot(Vmatrix.T,sensor_matrix.T))))
    L = np.linalg.cholesky(np.linalg.inv(Gamma_eta))
    H = np.dot(sensor_matrix,np.dot(Umatrix,np.dot(np.diag(zeta),np.dot(Umatrix.T,sensor_matrix.T))))
    # H = np.dot(sensor_matrix,np.dot(Hd,sensor_matrix.T))

    Ai = 0.5*np.log(np.linalg.det(np.identity(i+1)+np.dot(L.T,np.dot(H,L))))

    for j in range(i+1,ntargets):
        ur_index_all_tmp = ur_index_all.copy()
        ur_index_all_tmp[[i,j]]=ur_index_all_tmp[[j,i]]
        ur_index_tmp = ur_index_all_tmp[0:r]



        sensor_matrix = np.zeros((i+1,ntargets))
        for k in range(i+1):
            sensor_matrix[k][ur_index_tmp[k]] = 1
 
        # Gamma_eta = np.dot(sensor_matrix,np.dot(Gamma_eta_d,sensor_matrix.T))
        Gamma_eta = Gamma_n + np.dot(sensor_matrix,np.dot(Vmatrix,np.dot(np.diag(Gamma),np.dot(Vmatrix.T,sensor_matrix.T))))
        L = np.linalg.cholesky(np.linalg.inv(Gamma_eta))
        H = np.dot(sensor_matrix,np.dot(Umatrix,np.dot(np.diag(zeta),np.dot(Umatrix.T,sensor_matrix.T))))
        # H = np.dot(sensor_matrix,np.dot(Hd,sensor_matrix.T))

        Aj = 0.5*np.log(np.linalg.det(np.identity(i+1)+np.dot(L.T,np.dot(H,L))))


        if Aj>Ai:#np.abs(Aj) > np.abs(Ai):
            count += 1
            ur_index_all = ur_index_all_tmp.copy()
            ur_index = ur_index_tmp.copy()
            Ai = Aj.copy()
print("count of swap:",count)
sensor = np.sort(ur_index)

# trace.append(post_tr)
D = D_op(sensor,misfit,Gamma_z,FtQt)
det.append(D)
sensor_all.append(sensor)
print("sensor:",sensor)
print("EIG:", D)
############################################################################
# choices = list(combinations(np.arange(ntargets),r))
Test = 200#len(choices)


#############################################################################
filename = 'adv_num_obs_' + str(ntargets) + '_'+ str(r) + '_' + str(rall) + '_test_' + str(Test)
np.savez(filename,sensor=sensor,det=det)


for test in range(1,Test+1):
    if r > 1:
        sensor = np.random.choice(ntargets, size=r, replace=False, p=None)#np.array(choices[test-1])
    else:
        sensor = [test-1]
    D = D_op(sensor,misfit,Gamma_z,FtQt)

    sensor = np.sort(sensor)
    sensor_all.append(sensor)

    det.append(D)

    print(test)
    print("sensor:",sensor)
    print("EIG:", D)

    # filename = 'num_obs_' + str(ntargets) + '_'+ str(r) + '_' + str(rall) + '_test_' + str(Test)
    np.savez(filename,sensor=sensor_all,det=det)



