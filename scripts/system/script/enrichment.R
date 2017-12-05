#--------------------------------------------#
Signature.File   <- commandArgs(TRUE)[1]
HG2GO.RData.File <- commandArgs(TRUE)[2]
Out.File         <- commandArgs(TRUE)[3]
#--------------------------------------------#

#--------------------------------------------#
print("Signature.File is loading...")
Signature.Data <- as.matrix(read.table(Signature.File,header=FALSE,sep="\t",quote=""))
Signature.Data <- gsub("^ +","",Signature.Data)
print("Signature.File loaded!")

print("HG2GO.RData is loading...")
load(HG2GO.RData.File)
print("HG2GO.RData loaded!")
#--------------------------------------------#

#--------------------------------------------#
N.HGIDs <- unique(Signature.Data[,3])
N       <- length(N.HGIDs)
R.HGIDs <- unique(Signature.Data[which(as.double(Signature.Data[,5]) != "0"),3])
R       <- length(R.HGIDs)
#--------------------------------------------#

#--------------------------------------------#
All.GOTerms <- unique(HG2GO[which((HG2GO[,1] %in% R.HGIDs) == TRUE),][,2])
Sub.HG2GO   <- HG2GO[which((HG2GO[,1] %in% N.HGIDs) == TRUE & (HG2GO[,2] %in% All.GOTerms)),]
#--------------------------------------------#

#--------------------------------------------#
m <- matrix(ncol=7,nrow=length(All.GOTerms))
colnames(m) <- c("r","R","n","N","r/R","p","p(BH)")
rownames(m) <- All.GOTerms
m[,2] <- R
m[,4] <- N
for (GOTerm in All.GOTerms) {
    n.HGIDs <- unique(Sub.HG2GO[which(Sub.HG2GO[,2] == GOTerm),1])
    r.HGIDs <- intersect(n.HGIDs,R.HGIDs)
    m[GOTerm,1] <- length(r.HGIDs)    
    m[GOTerm,3] <- length(n.HGIDs)
}
#--------------------------------------------#
m[,5] <- m[,1]/m[,2]
m[,6] <- phyper(m[,1]-1,m[,3],m[,4]-m[,3],m[,2],lower.tail=FALSE)
m[,7] <- p.adjust(m[,6],method="BH")
#--------------------------------------------#

#--------------------------------------------#
m <- m[sort(m[,6],index.return=TRUE,decreasing=FALSE)$ix,,drop=FALSE]
#--------------------------------------------#

write.table(m,file=Out.File,row.names=TRUE,col.names=FALSE,sep="\t",quote=FALSE)