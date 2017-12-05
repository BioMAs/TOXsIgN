#--------------------------------------------#
PrepEnrichment.File <- commandArgs(TRUE)[1]
Out.File            <- commandArgs(TRUE)[2]
#--------------------------------------------#

#--------------------------------------------#
print("PrepEnrichment.File is loading...")
Data <- gsub("^ +","",as.matrix(read.table(PrepEnrichment.File,header=FALSE,sep="\t",quote="")))
print("PrepEnrichment.File loaded!")
#--------------------------------------------#

#--------------------------------------------#
New.Data <- matrix(ncol=10,nrow=nrow(Data))
New.Data[,1:6] <- Data[,1:6]
New.Data[,10] <- Data[,7]
#--------------------------------------------#

#--------------------------------------------#
r <- as.double(Data[,3])
R <- as.double(Data[,4])
n <- as.double(Data[,5])
N <- as.double(Data[,6])

New.Data[,7] <- r/(R+n-r)
New.Data[,8] <- phyper(r-1,n,N-n,R,lower.tail=FALSE)
#--------------------------------------------#

#--------------------------------------------#
Types <- unique(New.Data[,1])
for (Type in Types) {
    INDEXES              <- which(New.Data[,1] == Type)
    New.Data[INDEXES,9] <- p.adjust(New.Data[INDEXES,8],method="BH")
}
#--------------------------------------------#

#--------------------------------------------#
New.Data <- New.Data[sort(as.double(New.Data[,8]),index.return=TRUE,decreasing=FALSE)$ix,,drop=FALSE]
#--------------------------------------------#

#--------------------------------------------#
write.table(gsub("^ +","",New.Data),file=Out.File,row.names=FALSE,col.names=FALSE,sep="\t",quote=FALSE)
#--------------------------------------------#
quit()